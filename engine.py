import binascii
import io
import mimetypes
import os
import logging
import markdown
import pytz
import subprocess
import zipfile
import tempfile
import traceback
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import partial
from io import BytesIO
from urllib.parse import urlparse
from pypdf import PdfReader, PdfWriter
import re
import barcode
import jinja2
import jinja2.ext
import qrcode
import qrcode.image.svg
from ppf.datamatrix import DataMatrix
import weasyprint
from babel import dates, numbers, support
from barcode.writer import SVGWriter
from openpyxl import Workbook
from bs4 import BeautifulSoup

from trytond.config import config
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.model.fields.selection import TranslatedSelection
from trytond.model.modelstorage import _record_eval_pyson
from trytond.pool import Pool
from trytond.tools import file_open, slugify
from trytond.transaction import Transaction
from trytond.tools import grouped_slice
from trytond.report import Report
from trytond.modules.widgets import tools

from . import words
from .generator import PdfGenerator
from .tools import save_virtual_workbook, _convert_str_to_float

MEDIA_TYPE = config.get('html_report', 'type', default='screen')
RAISE_USER_ERRORS = config.getboolean('html_report', 'raise_user_errors',
    default=False)
DEFAULT_MIME_TYPE = config.get('html_report', 'mime_type', default='image/png')

# Determines if on merge, resulting PDF should be compacted using ghostscript
COMPACT_ON_MERGE = config.get('html_report', 'compact_on_merge',
    default=False)

logger = logging.getLogger(__name__)


def strfdelta(tdelta, fmt):
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    d['minutes'] = '%02d' % d['minutes']
    d['seconds'] = '%02d' % d['seconds']
    if not 'days' in fmt and d.get('days') > 0:
        d["hours"] += d.get('days') * 24 # 24h/day
    return fmt.format(**d)

class DualRecordError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class SwitchableTranslations:
    '''
    Class that implements ugettext() and ngettext() as expected by
    jinja2.ext.i18n but also adds the ability to switch the language
    at any point in a template.

    The class is used by SwitchableLanguageExtension
    '''
    def __init__(self, lang='en', dirname=None, domain=None):
        self.dirname = dirname
        self.domain = domain
        self.cache = {}
        self.env = None
        self.current = None
        self.language = lang
        self.report = None
        self.set_language(lang)

    # TODO: We should implement a context manager

    def set_language(self, lang='en'):
        self.language = lang
        if lang in self.cache:
            self.current = self.cache[lang]
            return

        context = Transaction().context
        if context.get('report_translations'):
            report_translations = context['report_translations']
            if os.path.isdir(report_translations):
                self.current = support.Translations.load(
                    dirname=report_translations,
                    locales=[lang],
                    domain=self.domain,
                    )
                self.cache[lang] = self.current
        else:
            self.report = context.get('html_report', -1)

    def ugettext(self, message):
        Report = Pool().get('ir.action.report')

        if self.current:
            return self.current.ugettext(message)
        elif self.report:
            return Report.gettext(self.report, message, self.language)
        return message

    def ngettext(self, singular, plural, n):
        Report = Pool().get('ir.action.report')

        if self.current:
            return self.current.ugettext(singular, plural, n)
        elif self.report:
            return Report.gettext(self.report, singular, self.language)
        return singular

# Based on
# https://stackoverflow.com/questions/44882075/switch-language-in-jinja-template/45014393#45014393

class SwitchableLanguageExtension(jinja2.ext.Extension):
    '''
    This Jinja2 Extension allows the user to use the folowing tag:

    {% language 'en' %}
    {% endlanguage %}

    All gettext() calls within the block will return the text in the language
    defined thanks to the use of SwitchableTranslations class.
    '''
    tags = {'language'}

    def __init__(self, env):
        self.env = env
        env.extend(
            install_switchable_translations=self._install,
            )
        self.translations = None

    def _install(self, translations):
        self.env.install_gettext_translations(translations)
        self.translations = translations

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        # Parse the language code argument
        context = jinja2.nodes.ContextReference()
        args = [parser.parse_expression(), context]
        # Parse everything between the start and end tag:
        body = parser.parse_statements(['name:endlanguage'], drop_needle=True)
        node = self.call_method('_switch_language', args, lineno=lineno)
        # Call the _switch_language method with the given language code and body
        return jinja2.ext.nodes.CallBlock(node, [], [], body).set_lineno(lineno)

    def _switch_language(self, language_code, context, caller):
        if self.translations:
            self.translations.set_language(language_code)
        with Transaction().set_context(language=language_code):
            record = context.get('record')
            if isinstance(record, DualRecord):
                record.refresh()
            records = context.get('records')
            if isinstance(records, (tuple, list)):
                for record in records:
                    if isinstance(record, DualRecord):
                        record.refresh()
            output = caller()
        return output


class Formatter:
    def __init__(self):
        self.__langs = {}

    def format(self, record, field, value):
        formatter = '_formatted_%s' % field._type
        method = getattr(self, formatter, self._formatted_raw)
        return method(record, field, value)

    def _get_lang(self):
        Lang = Pool().get('ir.lang')
        locale = Transaction().context.get('report_lang', Transaction().language)
        lang = self.__langs.get(locale)
        if lang:
            return lang
        langs = Lang.search([('code', '=', locale or 'en')], limit=1)
        lang = langs[0] if langs else 'en'
        self.__langs[locale] = lang
        return lang

    def _formatted_raw(self, record, field, value):
        return value

    def _formatted_many2one(self, record, field, value):
        if not value:
            return value
        return FormattedRecord(value, self)

    def _formatted_one2one(self, record, field, value):
        return self._formatted_many2one(record, field, value)

    def _formatted_reference(self, record, field, value):
        return self._formatted_many2one(record, field, value)

    def _formatted_one2many(self, record, field, value):
        if not value:
            return value
        return [FormattedRecord(x) for x in value]

    def _formatted_many2many(self, record, field, value):
        return self._formatted_one2many(record, field, value)

    def _formatted_boolean(self, record, field, value):
        return (gettext('html_report.msg_yes') if value else
            gettext('html_report.msg_no'))

    def _formatted_date(self, record, field, value):
        if value is None:
            return ''
        return self._get_lang().strftime(value)

    def _formatted_datetime(self, record, field, value):
        if value is None:
            return ''
        return self._get_lang().strftime(value)

    def _formatted_timestamp(self, record, field, value):
        return self._formatted_datetime(record, field, value)

    def _formatted_timedelta(self, record, field, value):
        if value is None:
            return ''
        return strfdelta(value, '{hours}:{minutes}')

    def _formatted_char(self, record, field, value):
        if value is None:
            return ''
        Model = Pool().get(record.__name__)
        value = getattr(Model(record.id), field.name)
        return value.replace('\n', '<br/>')

    def _formatted_text(self, record, field, value):
        return self._formatted_char(record, field, value)

    def _formatted_integer(self, record, field, value):
        if value is None:
            return ''
        return str(value)

    def _formatted_float(self, record, field, value, grouping=True, monetary=None):
        if value is None:
            return ''
        digits = field.digits
        if isinstance(digits, str):
            digits = getattr(record, digits).digits if getattr(record, digits) else None
        else:
            # TODO remove from issue10677
            if digits:
                digits = digits[1]
        if not isinstance(digits, int):
            digits = _record_eval_pyson(record, digits,
                encoded=False)
        if digits is None:
            d = value
            if not isinstance(d, Decimal):
                d = Decimal(repr(value))
            digits = -int(d.as_tuple().exponent)
        return self._get_lang().format('%.' + str(digits) + 'f', value,
            grouping=grouping, monetary=monetary)

    def _formatted_numeric(self, record, field, value):
        return self._formatted_float(record, field, value)

    def _formatted_binary(self, record, field, value):
        if not value:
            return
        value = binascii.b2a_base64(value)
        value = value.decode('ascii')
        filename = field.filename
        mimetype = None
        if filename:
            mimetype = mimetypes.guess_type(filename)[0]
        if not mimetype:
            mimetype = DEFAULT_MIME_TYPE
        return ('data:%s;base64,%s' % (mimetype, value)).strip()

    def _formatted_selection(self, record, field, value):
        if value is None:
            return ''

        Model = Pool().get(record.__name__)
        record = Model(record.id)
        t  = TranslatedSelection(field.name)
        return t.__get__(record, record).replace('\n', '<br/>')

    # TODO: Implement: dict, multiselection


class FormattedRecord:
    def __init__(self, record, formatter=None):
        self._raw_record = record
        if formatter:
            self.__formatter = formatter
        else:
            self.__formatter = Formatter()

    def __getattr__(self, name):
        value = getattr(self._raw_record, name)
        field = self._raw_record._fields.get(name)
        if not field:
            return value
        return self.__formatter.format(self._raw_record, field, value)


class DualRecord:
    def __init__(self, record, formatter=None):
        self.raw = record
        self._formatter = formatter
        if not self._formatter:
            self._formatter = Formatter()
        self.render = FormattedRecord(record, self._formatter)

    def __getattr__(self, name):
        field = self.raw._fields.get(name)
        if not field:
            raise DualRecordError('Field "%s" not found in record of model '
                '"%s".' % (name, self.raw.__name__))
        if field._type not in {'many2one', 'one2one', 'reference', 'one2many',
                'many2many'}:
            raise DualRecordError('You are trying to access field "%s" of type '
                '"%s" in a DualRecord of model "%s". You must use "raw." or '
                '"render." before the field name.' % (name, field._type,
                    self.raw.__name__))
        value = getattr(self.raw, name)
        if not value:
            return value
        if field._type in {'many2one', 'one2one', 'reference'}:
            return DualRecord(value, self._formatter)
        return [DualRecord(x, self._formatter) for x in value]

    @property
    def _attachments(self):
        pool = Pool()
        Attachment = pool.get('ir.attachment')
        return [DualRecord(x, self._formatter) for x in
            Attachment.search([('resource', '=', str(self.raw))])]

    @property
    def _notes(self):
        pool = Pool()
        Note = pool.get('ir.note')
        return [DualRecord(x, self._formatter) for x in
            Note.search([('resource', '=', str(self.raw))])]

    def refresh(self):
        'Re-instantiates the object using the current context. '
        'This can be useful if the DualRecord instance was outside '
        'the {% language %} tag.'
        self.raw = self.raw.__class__(self.raw.id)
        self.render = FormattedRecord(self.raw, self._formatter)


class HTMLReportMixin:
    __slots__ = ()
    babel_domain = 'messages'
    side_margin = 2
    extra_vertical_margin = 30

    @classmethod
    def _get_dual_records(cls, ids, model, data):
        records = cls._get_records(ids, model, data)
        return [DualRecord(x) for x in records]

    @classmethod
    def get_templates_jinja(cls, action):
        header = action.html_header_content
        content = (action.report_content
            and action.report_content.decode("utf-8") or action.html_content)
        footer = action.html_footer_content
        last_footer = action.html_last_footer_content
        if not content:
            if not action.html_content:
                raise Exception('Error', 'Missing jinja report file!')
            content = action.html_content
        return header, content, footer, last_footer

    @classmethod
    def merge_pdfs(cls, pdfs_data):
        merger = PdfWriter()
        for pdf_data in pdfs_data:
            tmppdf = BytesIO(pdf_data)
            merger.append(PdfReader(tmppdf))
            tmppdf.close()

        if COMPACT_ON_MERGE:
            # Use ghostscript to compact PDF which will usually remove
            # duplicated images. It can make a PDF go from 17MB to 1.8MB,
            # for example.
            path = tempfile.mkdtemp()
            merged_path = os.path.join(path, 'merged.pdf')
            merged = open(merged_path, 'wb')
            merger.write(merged)
            merged.close()

            compacted_path = os.path.join(path, 'compacted.pdf')
            # changed PDFSETTINGS from /printer to /prepress
            command = ['gs', '-q', '-dBATCH', '-dNOPAUSE', '-dSAFER',
                '-sDEVICE=pdfwrite', '-dPDFSETTINGS=/prepress',
                '-sOutputFile=%s' % compacted_path, merged_path]
            subprocess.call(command)

            f = open(compacted_path, 'r')
            try:
                pdf_data = f.read()
            finally:
                f.close()
        else:
            tmppdf = BytesIO()
            merger.write(tmppdf)
            pdf_data = tmppdf.getvalue()
            merger.close()
            tmppdf.close()

        return pdf_data

    @classmethod
    def __execute(cls, ids, data, queue=None):
        action, model = cls.get_action(data)
        cls.check_access(action, model, ids)

        # in case is not jinja, call super()
        if action.template_extension != 'jinja':
            return super().execute(ids, data)
        action_name = cls.get_name(action)
        side_margin = action.html_side_margin
        if side_margin is None:
            side_margin = cls.side_margin
        extra_vertical_margin = action.html_extra_vertical_margin
        if extra_vertical_margin is None:
            extra_vertical_margin = cls.extra_vertical_margin

        output_format = data.get('output_format', action.extension or 'pdf')
        # use DualRecord when template extension is jinja
        data['html_dual_record'] = True
        records = []
        with Transaction().set_context(
                html_report=action.id,
                address_with_party=False,
                output_format=output_format):
            if model and ids:
                records = cls._get_dual_records(ids, model, data)

                suffix = '-'.join(r.render.rec_name for r in records[:5])
                if len(records) > 5:
                    suffix += '__' + str(len(records[5:]))
                filename = slugify('%s-%s' % (action_name, suffix))
            else:
                records = []
                filename = slugify(action_name)

            # report single and len > 1, return zip file
            if action.single and len(ids) > 1 and action.html_zipped:
                content = BytesIO()
                with zipfile.ZipFile(content, 'w') as content_zip:
                    for record in records:
                        oext, rcontent = cls._execute_html_report(
                            [record],
                            data,
                            action,
                            side_margin=side_margin,
                            extra_vertical_margin=extra_vertical_margin)
                        rfilename = '%s.%s' % (
                            slugify(record.render.rec_name),
                            oext)
                        if action.html_copies and action.html_copies > 1:
                            rcontent = cls.merge_pdfs([rcontent] * action.html_copies)
                        content_zip.writestr(rfilename, rcontent)
                content = content.getvalue()
                return ('zip', content, False, filename)

            oext, content = cls._execute_html_report(
                    records,
                    data,
                    action,
                    side_margin=side_margin,
                    extra_vertical_margin=extra_vertical_margin)
            if content is None:
                content = ''
            if not isinstance(content, str):
                content = bytes(content)

            if action.html_copies and action.html_copies > 1:
                content = cls.merge_pdfs([content] * action.html_copies)
            Printer = None
            try:
                Printer = Pool().get('printer')
            except KeyError:
                logger.warning('Model "Printer" not found.')
            if Printer:
                return Printer.send_report(oext, content,
                    action_name, action)
            return oext, content, cls.get_direct_print(action), filename

    @classmethod
    def execute(cls, ids, data):
        action, model = cls.get_action(data)
        cls.check_access(action, model, ids)
        if action.template_extension != 'jinja':
            return super().execute(ids, data)
        return cls.__execute(ids, data, queue=None)

    @classmethod
    def _execute_html_report(cls, records, data, action, side_margin=2,
            extra_vertical_margin=30):
        header_template, main_template, footer_template, last_footer_template = \
                cls.get_templates_jinja(action)
        extension = data.get('output_format', action.extension or 'pdf')
        if action.single:
            # If document requires a page counter for each record we need to
            # render records individually
            documents = []
            for record in records:
                content = cls.render_template_jinja(action, main_template,
                    record=record, records=[record], data=data)
                header = header_template and cls.render_template_jinja(action,
                    header_template, record=record, records=[record],
                    data=data)
                footer = footer_template and cls.render_template_jinja(action,
                    footer_template, record=record, records=[record],
                    data=data)
                last_footer = last_footer_template and cls.render_template_jinja(action,
                    last_footer_template, record=record, records=[record],
                    data=data)
                if extension == 'pdf':
                    documents.append(PdfGenerator(
                            content,
                            header_html=header,
                            footer_html=footer,
                            last_footer_html=last_footer,
                            side_margin=side_margin,
                            extra_vertical_margin=extra_vertical_margin).render_html())
                else:
                    documents.append(content)
            if extension == 'pdf' and documents:
                document = documents[0].copy([page for doc in documents
                    for page in doc.pages])
                document = document.write_pdf()
            else:
                document = ''.join(documents)
        else:
            content = cls.render_template_jinja(action, main_template,
                records=records, data=data)
            header = header_template and cls.render_template_jinja(action,
                header_template, records=records, data=data)
            footer = footer_template and cls.render_template_jinja(action,
                footer_template, records=records, data=data)
            last_footer = last_footer_template and cls.render_template_jinja(action,
                last_footer_template, records=records, data=data)
            if extension == 'pdf':
                document = PdfGenerator(
                    content,
                    header_html=header,
                    footer_html=footer,
                    last_footer_html=last_footer,
                    side_margin=side_margin,
                    extra_vertical_margin=extra_vertical_margin
                    ).render_pdf()
            else:
                document = content

        if extension == 'xlsx':
            wb = Workbook()
            ws = wb.active

            soup = BeautifulSoup(document, 'html.parser')
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    data = []
                    for cell in row.find_all(['td', 'th']):
                        data.append(_convert_str_to_float(cell.text))
                    ws.append(data)
                document = save_virtual_workbook(wb)
        return extension, document

    @classmethod
    def get_action(cls, data):
        pool = Pool()
        ActionReport = pool.get('ir.action.report')

        action_id = data.get('action_id')
        if action_id is None:
            action_reports = ActionReport.search([
                    ('report_name', '=', cls.__name__)
                    ])
            assert action_reports, '%s not found' % cls
            action = action_reports[0]
        else:
            action = ActionReport(action_id)

        return action, action.model or data.get('model')

    @classmethod
    def get_name(cls, action):
        return action.name

    @classmethod
    def get_direct_print(cls, action):
        return action.direct_print

    @classmethod
    def jinja_loader_func(cls, name):
        """
        Return the template from the module directories or ID from other template.

        The name is expected to be in the format:

            <module_name>/path/to/template

        for example, if the account_invoice_html_report module had a base
        template in its reports folder, then you should be able to use:

            {% extends 'html_report/report/base.html' %}
        """
        Template = Pool().get('html.template')

        if '/' in name:
            module, path = name.split('/', 1)
            try:
                with file_open(os.path.join(module, path)) as f:
                    return f.read()
            except IOError:
                return None
        else:
            template, = Template.search([('id', '=', name)], limit=1)
            return template.all_content

    @classmethod
    def get_jinja_filters(cls):
        """
        Returns filters that are made available in the template context.
        By default, the following filters are available:

        * render: Renders value depending on its type
        * modulepath: Returns the absolute path of a file inside a
            tryton-module (e.g. sale/sale.css)

        For additional arguments that can be passed to these filters,
        refer to the Babel `Documentation
        <http://babel.edgewall.org/wiki/Documentation>`_.
        """
        Lang = Pool().get('ir.lang')

        def module_path(name):
            module, path = name.split('/', 1)
            with file_open(os.path.join(module, path)) as f:
                return 'file://' + f.name

        def base64(name):
            module, path = name.split('/', 1)
            with file_open(os.path.join(module, path), 'rb') as f:
                value = binascii.b2a_base64(f.read())
                value = value.decode('ascii')
                mimetype = mimetypes.guess_type(f.name)[0]
                if not mimetype:
                    mimetype = DEFAULT_MIME_TYPE
                return ('data:%s;base64,%s' % (mimetype, value)).strip()

        def render(value, digits=2, lang=None, filename=None):
            context = Transaction().context
            if not lang:
                langs = Lang.search([('code', '=', 'en')], limit=1)
                lang = langs[0] if langs else 'en'
            if isinstance(value, (float, Decimal)):
                grouping = not context.get('output_format') in ['xls', 'xlsx']
                return lang.format('%.*f', (digits, value), grouping=grouping)
            if value is None or value == '':
                return ''
            if isinstance(value, bool):
                return (gettext('html_report.msg_yes') if value else
                    gettext('html_report.msg_no'))
            if isinstance(value, int):
                return lang.format('%d', value, grouping=True)
            if hasattr(value, 'rec_name'):
                return value.rec_name
            if isinstance(value, datetime):
                return lang.strftime(value)
            if isinstance(value, date):
                return lang.strftime(value)
            if isinstance(value, timedelta):
                return strfdelta(value, '{hours}:{minutes}')
            if isinstance(value, str):
                return value.replace('\n', '<br/>')
            if isinstance(value, bytes):
                value = binascii.b2a_base64(value)
                value = value.decode('ascii')
                mimetype = None
                if filename:
                    mimetype = mimetypes.guess_type(filename)[0]
                if not mimetype:
                    mimetype = DEFAULT_MIME_TYPE
                return ('data:%s;base64,%s' % (mimetype, value)).strip()
            return value

        def nullslast(tuple_list):
            if not isinstance(tuple_list, list):
                raise UserError(gettext(
                    'html_report.nullslat_incorrect_format'))
            if not all(isinstance(t, tuple) for t in tuple_list):
                raise UserError(gettext(
                    'html_report.nullslat_incorrect_format'))
            none_elements = []
            non_none_elements = []
            for t in tuple_list:
                if t[0]:
                    non_none_elements.append(t)
                else:
                    none_elements.append(t)
            return non_none_elements + none_elements

        def short_url(value):
            pattern = r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.]/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.]\b/?(?!@)))"""
            find_urls = re.findall(pattern, value)

            for furl in find_urls:
                netloc = urlparse(furl).netloc
                if netloc:
                    r = (furl, '<a href="%s">%s</a>' % (furl, netloc))
                    value = value.replace(*r)
            return value

        locale = Transaction().context.get('report_lang',
            Transaction().language).split('_')[0]
        langs = Lang.search([
                ('code', '=', locale or 'en'),
                ], limit=1)
        lang = langs[0] if langs else 'en'
        return {
            'base64': base64,
            'currencyformat': partial(numbers.format_currency, locale=locale),
            'decimalformat': partial(numbers.format_decimal, locale=locale),
            'dateformat': partial(dates.format_date, locale=locale),
            'datetimeformat': partial(dates.format_datetime, locale=locale),
            'integer_to_words': words.integer_to_words,
            'format_currency': Report.format_currency,
            'format_date': Report.format_date,
            'format_datetime': Report.format_datetime,
            'format_number': Report.format_number,
            'format_timedelta': Report.format_timedelta,
            'grouped_slice': grouped_slice,
            'js_plus_js': tools.js_plus_js,
            'js_to_html': partial(tools.js_to_html, url_prefix='base64'),
            'js_to_text': tools.js_to_text,
            'markdown': markdown.markdown,
            'modulepath': module_path,
            'nullslast': nullslast,
            'numberformat': partial(numbers.format_number, locale=locale),
            'number_to_words': words.number_to_words,
            'render': partial(render, lang=lang),
            'percentformat': partial(numbers.format_percent, locale=locale),
            'scientificformat': partial(
                numbers.format_scientific, locale=locale),
            'short_url': short_url,
            'timedeltaformat': partial(dates.format_timedelta, locale=locale),
            'timeformat': partial(dates.format_time, locale=locale),
            }

    @classmethod
    def get_environment(cls):
        """
        Create and return a jinja environment to render templates

        Downstream modules can override this method to easily make changes
        to environment
        """
        extensions = ['jinja2.ext.i18n', 'jinja2.ext.loopcontrols', 'jinja2.ext.do',
            SwitchableLanguageExtension]
        env = jinja2.Environment(extensions=extensions,
            loader=jinja2.FunctionLoader(cls.jinja_loader_func))
        env.filters.update(cls.get_jinja_filters())

        context = Transaction().context
        locale = context.get(
            'report_lang', Transaction().language or 'en').split('_')[0]
        report_translations = context.get('report_translations')
        if report_translations and os.path.isdir(report_translations):
            translations = SwitchableTranslations(
                locale, report_translations, cls.babel_domain)
        else:
            translations = SwitchableTranslations(locale)
        env.install_switchable_translations(translations)
        return env

    @classmethod
    def label(cls, model, field=None, lang=None):
        pool = Pool()
        Translation = pool.get('ir.translation')
        Model = pool.get('ir.model')

        if not lang:
            lang = Transaction().language

        if not model:
            return ''

        if field == None:
            model, = Model.search([('name', '=', model)])
            return model.string
        else:
            args = ("%s,%s" % (model, field), 'field', lang, None)
            translation = Translation.get_sources([args])

            if translation[args]:
                return translation[args]
            else:
                args = ("%s,%s" % (model, field), 'field', 'en', None)
                translation = Translation.get_sources([args])

                if translation[args]:
                    return translation[args]

            ModelObject = pool.get(model)
            return getattr(ModelObject, field).string

    @classmethod
    def message(cls, message_id, *args, **variables):
        return gettext(message_id, *args, **variables)

    @classmethod
    def qrcode(cls, value):
        qr_code = qrcode.make(value, image_factory=qrcode.image.svg.SvgImage)
        stream = io.BytesIO()
        qr_code.save(stream=stream)
        return cls.to_base64(stream.getvalue())

    @classmethod
    def barcode(cls, _type, value, text=None, **options):
        # For the list of available options see:
        # https://python-barcode.readthedocs.io/en/latest/writers.html
        ean_class = barcode.get_barcode_class(_type)
        ean_code = ean_class(value, writer=SVGWriter()).render(options, text)
        return cls.to_base64(ean_code)

    @classmethod
    def datamatrix(cls, value):
        matrix = DataMatrix(value)
        return cls.to_base64(bytes(matrix.svg(), 'utf-8'))

    @staticmethod
    def to_base64(value):
        value = binascii.b2a_base64(value)
        value = value.decode('ascii')
        mimetype = "image/svg+xml"
        return ('data:%s;base64,%s' % (mimetype, value)).strip()

    @classmethod
    def dualrecord(cls, record):
        if not record:
            return
        if isinstance(record, str):
            model, id = record.split(',')
            record = Pool().get(model)(id)
        return DualRecord(record)

    @classmethod
    def raise_user_error(cls, value):
        raise UserError(value)


    @classmethod
    def render_template_jinja(cls, action, template_string, record=None,
            records=None, data=None):
        """
        Render the template using Jinja2
        """
        pool = Pool()
        User = pool.get('res.user')
        try:
            Company = pool.get('company.company')
        except:
            Company = None

        env = cls.get_environment()

        if records is None:
            records = []

        now = datetime.now()
        context = {
            'barcode': cls.barcode,
            'data': data,
            'datamatrix': cls.datamatrix,
            'Decimal': Decimal,
            'dualrecord': cls.dualrecord,
            'qrcode': cls.qrcode,
            'label': cls.label,
            'message': cls.message,
            'pool': Pool(),
            'raise_user_error': cls.raise_user_error,
            'record': record,
            'records': records,
            'report': DualRecord(action) if action else None,
            'time': now,
            'timedelta': timedelta,
            'user': DualRecord(User(Transaction().user)),
            'utc_time': now,
            }
        company_id = Transaction().context.get('company')
        if Company and company_id:
            company = Company(company_id)
            context['company'] = DualRecord(company)
            if company.timezone:
                timezone = pytz.timezone(company.timezone)
                tznow = timezone.localize(now)
                tznow = now + tznow.utcoffset()
                context['time'] = tznow

        context.update(cls.local_context())
        try:
            report_template = env.from_string(template_string)
        except jinja2.exceptions.TemplateSyntaxError as e:
            if RAISE_USER_ERRORS or action.html_raise_user_error:
                raise UserError(gettext('html_report.template_error',
                        report=action.rec_name, error=repr(e)))
            raise
        try:
            res = report_template.render(**context)
        except Exception as e:
            o = traceback.TracebackException.from_exception(e)
            lineno = None
            for line in reversed(o.stack):
                if line.filename == '<template>':
                    lineno = line.lineno
                    break
            if lineno:
                location = []
                location.append('Line %s' % lineno)
                lines = template_string.splitlines()
                for line in reversed(lines[:lineno]):
                    if re.match(r'^\s*{%\s*endmacro\s+', line):
                        location.append('(not in a macro)')
                        break
                    if re.match(r'^\s*{%\s*macro\s+', line):
                        location.append('Macro %s' % line.split()[2])
                        break
                location.append('Expr: %s' %
                    template_string.splitlines()[lineno-1])
                e.args = e.args + tuple(location)

            if RAISE_USER_ERRORS or action and action.html_raise_user_error:
                raise UserError(gettext('html_report.render_error',
                        report=action.rec_name, error=repr(e)))
            raise
        return res

    @classmethod
    def local_context(cls):
        return {}

    @classmethod
    def weasyprint_render(cls, content):
        return weasyprint.HTML(string=content, media_type=MEDIA_TYPE).render()
