from io import BytesIO
import os
import zipfile

from dominate import document
from dominate.util import raw
from dominate.tags import body as body_tag, link, meta, style

from trytond.pool import Pool
from trytond.tools import file_open, slugify
from trytond.transaction import Transaction

from .engine import HTMLReportMixin
from .generator import PdfGenerator
from .engine import DualRecord


class DominateReportMixin(HTMLReportMixin):
    _single = False

    @classmethod
    def body(cls, action, record=None, records=None, data=None):
        raise NotImplementedError

    @classmethod
    def title(cls, action, record=None, records=None, data=None):
        if record:
            return cls.label(record.raw.__name__)
        if records:
            return cls.label(records[0].raw.__name__)
        if action and action.model:
            return cls.label(action.model)
        return action.name if action else ''

    @classmethod
    def main(cls, action, record=None, records=None, data=None):
        body_nodes = cls.body(action, record=record, records=records, data=data)
        title = cls.title(action, record=record, records=records, data=data)
        if body_nodes is None:
            body_nodes = []
        if not isinstance(body_nodes, (list, tuple)):
            body_nodes = [body_nodes]
        return cls.build_document(action, title, body_nodes)

    @classmethod
    def header(cls, action, record=None, records=None, data=None):
        return None

    @classmethod
    def footer(cls, action, record=None, records=None, data=None):
        return None

    @classmethod
    def last_footer(cls, action, record=None, records=None, data=None):
        return None

    @classmethod
    def _render_node(cls, node):
        if node is None:
            return None
        return node.render() if hasattr(node, 'render') else str(node)

    @classmethod
    def _module_path(cls, name):
        module, path = name.split('/', 1)
        with file_open(os.path.join(module, path)) as f:
            return 'file://' + f.name

    @classmethod
    def _base_css_href(cls):
        return cls._module_path('html_report/templates/base.css')

    @classmethod
    def _css_extension(cls, action):
        if not action:
            return None
        Signature = Pool().get('html.template.signature')
        Template = Pool().get('html.template')

        signatures = Signature.search([('name', '=', 'show_css_extension()')],
            limit=1)
        if not signatures:
            return None
        signature = signatures[0]

        if action:
            for report_template in action.html_templates:
                if report_template.signature == signature:
                    if report_template.template_used:
                        return report_template.template_used.content or ''

        templates = Template.search([('implements', '=', signature)], limit=1)
        return templates[0].content if templates else None

    @classmethod
    def _css_override(cls, action):
        if not action:
            return None
        Signature = Pool().get('html.template.signature')
        Template = Pool().get('html.template')

        signatures = Signature.search([('name', '=', 'show_css()')], limit=1)
        if not signatures:
            return None
        signature = signatures[0]

        if action:
            for report_template in action.html_templates:
                if report_template.signature == signature:
                    if report_template.template_used:
                        return report_template.template_used.content or ''

        templates = Template.search([('implements', '=', signature)], limit=1)
        return templates[0].content if templates else None

    @classmethod
    def build_document(cls, action, title, body_nodes):
        doc = document(title=title)
        doc['lang'] = 'en'
        with doc.head:
            meta(charset='utf-8')
            meta(name='description', content='')
            meta(name='author', content='Nantic')
            css_override = cls._css_override(action)
            if css_override:
                style(raw(css_override))
            else:
                link(rel='stylesheet', href=cls._base_css_href(),
                    type='text/css')
            css_ext = cls._css_extension(action)
            if css_ext:
                style(raw(css_ext))
        with doc:
            with body_tag(id='base', cls='main-report') as body_node:
                for node in body_nodes:
                    if node is None:
                        continue
                    if isinstance(node, str):
                        body_node.add(raw(node))
                    else:
                        body_node.add(node)
        return doc

    @classmethod
    def _get_language(cls, record):
        if record:
            if getattr(record.raw, 'party', None):
                party = record.party
                if party and party.raw.lang:
                    return party.raw.lang.code
            if getattr(record.raw, 'company', None):
                company = record.company
                if company and company.party and company.party.raw.lang:
                    return company.party.raw.lang.code
        return Transaction().language or 'en'

    @classmethod
    def _refresh_records(cls, records):
        if isinstance(records, DualRecord):
            records.refresh()
        elif isinstance(records, (tuple, list)):
            for record in records:
                if isinstance(record, DualRecord):
                    record.refresh()

    @classmethod
    def _execute_dominate_report(cls, records, data, action, side_margin=2,
            extra_vertical_margin=30):
        extension = data.get('output_format', action.extension or 'pdf')
        render_single = action.single or cls._single
        if render_single:
            documents = []
            for record in records:
                language = cls._get_language(record)
                with Transaction().set_context(language=language):
                    cls._refresh_records([record])
                    content = cls._render_node(cls.main(
                        action, record=record, records=[record], data=data))
                    header = cls._render_node(cls.header(
                        action, record=record, records=[record], data=data))
                    footer = cls._render_node(cls.footer(
                        action, record=record, records=[record], data=data))
                    last_footer = cls._render_node(cls.last_footer(
                        action, record=record, records=[record], data=data))

                if extension == 'pdf':
                    documents.append(PdfGenerator(
                        content,
                        header_html=header,
                        footer_html=footer,
                        last_footer_html=last_footer,
                        side_margin=side_margin,
                        extra_vertical_margin=extra_vertical_margin,
                    ).render_html())
                else:
                    documents.append(content)
            if extension == 'pdf' and documents:
                document = documents[0].copy([page for doc in documents
                    for page in doc.pages])
                document = document.write_pdf()
            else:
                document = ''.join(documents)
        else:
            language = cls._get_language(records[0] if records else None)
            with Transaction().set_context(language=language):
                cls._refresh_records(records)
                content = cls._render_node(cls.main(
                    action, records=records, data=data))
                header = cls._render_node(cls.header(
                    action, records=records, data=data))
                footer = cls._render_node(cls.footer(
                    action, records=records, data=data))
                last_footer = cls._render_node(cls.last_footer(
                    action, records=records, data=data))
            if extension == 'pdf':
                document = PdfGenerator(
                    content,
                    header_html=header,
                    footer_html=footer,
                    last_footer_html=last_footer,
                    side_margin=side_margin,
                    extra_vertical_margin=extra_vertical_margin,
                ).render_pdf()
            else:
                document = content

        if extension == 'xlsx':
            from bs4 import BeautifulSoup
            from openpyxl import Workbook
            from .tools import save_virtual_workbook, _convert_str_to_float

            wb = Workbook()
            ws = wb.active

            soup = BeautifulSoup(document, 'html.parser')
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    row_data = []
                    for cell in row.find_all(['td', 'th']):
                        row_data.append(_convert_str_to_float(cell.text))
                    ws.append(row_data)
                document = save_virtual_workbook(wb)
        return extension, document

    @classmethod
    def execute(cls, ids, data):
        action, model = cls.get_action(data)
        cls.check_access(action, model, ids)
        action_name = cls.get_name(action)
        side_margin = action.html_side_margin
        if side_margin is None:
            side_margin = cls.side_margin
        extra_vertical_margin = action.html_extra_vertical_margin
        if extra_vertical_margin is None:
            extra_vertical_margin = cls.extra_vertical_margin

        if Transaction().context.get('output_format') == 'html':
            is_zip, is_merge_pdf, Printer = None, None, None
            output_format = data['output_format'] = 'html'
        else:
            is_zip = action.single and len(ids) > 1 and action.html_zipped
            is_merge_pdf = action.html_copies and action.html_copies > 1
            Printer = None
            try:
                Printer = Pool().get('printer')
            except KeyError:
                pass
            output_format = data.get('output_format', action.extension or 'pdf')

        data['html_dual_record'] = True
        records = []
        with Transaction().set_context(
                html_report=action.id,
                address_with_party=False,
                output_format=output_format):
            if model and ids:
                records = cls._get_dual_records(ids, model, data)

                if action.html_file_name:
                    import jinja2

                    template = jinja2.Template(action.html_file_name)
                    filename = slugify('-'.join(template.render(record=record)
                        for record in records[:5]))
                else:
                    suffix = '-'.join(r.render.rec_name for r in records[:5])
                    if len(records) > 5:
                        suffix += '__' + str(len(records[5:]))
                    filename = slugify('%s-%s' % (action_name, suffix))
            else:
                records = []
                filename = slugify(action_name)

            if is_zip:
                content = BytesIO()
                with zipfile.ZipFile(content, 'w') as content_zip:
                    for record in records:
                        oext, rcontent = cls._execute_dominate_report(
                            [record],
                            data,
                            action,
                            side_margin=side_margin,
                            extra_vertical_margin=extra_vertical_margin)
                        rfilename = '%s.%s' % (
                            slugify(record.render.rec_name),
                            oext)
                        if action.html_copies and action.html_copies > 1:
                            rcontent = cls.merge_pdfs(
                                [rcontent] * action.html_copies)
                        content_zip.writestr(rfilename, rcontent)
                content = content.getvalue()
                return ('zip', content, False, filename)

            oext, content = cls._execute_dominate_report(
                records,
                data,
                action,
                side_margin=side_margin,
                extra_vertical_margin=extra_vertical_margin)
            if content is None:
                content = ''
            if not isinstance(content, str):
                content = bytes(content)

            if is_merge_pdf:
                content = cls.merge_pdfs([content] * action.html_copies)
            if Printer:
                return Printer.send_report(oext, content,
                    action_name, action)
            return oext, content, cls.get_direct_print(action), filename
