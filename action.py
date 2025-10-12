# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import PoolMeta, Pool
from trytond.model import ModelSQL, ModelView, fields
from trytond.pyson import Eval
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.cache import Cache
from trytond.ir.lang import get_parent_language


class ActionReport(metaclass=PoolMeta):
    __name__ = 'ir.action.report'
    html_template = fields.Many2One('html.template', 'Body',
        domain=[
            ('type', 'in', ['base', 'extension']),
            ],
        states={
            'invisible': Eval('template_extension') != 'jinja',
            })
    jinja_template = fields.Text('Jinja Template',
        states={
            'invisible': Eval('template_extension') != 'jinja',
            })
    html_header_template = fields.Many2One('html.template', 'Header',
        domain=[
            ('type', '=', 'header'),
            ],
        states={
            'invisible': Eval('template_extension') != 'jinja',
            })
    html_footer_template = fields.Many2One('html.template', 'Footer',
        domain=[
            ('type', '=', 'footer'),
            ],
        states={
            'invisible': Eval('template_extension') != 'jinja',
            })
    html_last_footer_template = fields.Many2One('html.template',
        'Last Page Footer', domain=[
            ('type', '=', 'footer'),
            ],
        states={
            'invisible': Eval('template_extension') != 'jinja',
            })
    html_templates = fields.One2Many('html.report.template', 'report', 'Templates',
        states={
            'invisible': Eval('template_extension') != 'jinja',
            })
    html_content = fields.Function(fields.Text('Content',
        states={
                'invisible': Eval('template_extension') != 'jinja',
        }), 'get_content')
    html_raise_user_error = fields.Boolean('Raise User Error',
        help='Will raise a UserError in case of error in template parsing.')
    html_translations = fields.One2Many('html.template.translation', 'report',
        'Translations')
    _html_translation_cache = Cache('html.template.translation', context=False)
    html_header_content = fields.Function(fields.Text('Header Content'),
        'get_content')
    html_footer_content = fields.Function(fields.Text('Footer Content'),
        'get_content')
    html_last_footer_content = fields.Function(fields.Text(
            'Last Page Footer Content'), 'get_content')
    html_zipped = fields.Boolean('Zipped', states={
        'invisible': ~Eval('single'),
        },
        help='If set, a zip file with a document per record will be created.')
    html_copies = fields.Integer('Number of copies')
    html_side_margin = fields.Integer('Side Margin (cm)')
    html_extra_vertical_margin = fields.Integer('Extra Vertical Margin (cm)')
    html_file_name = fields.Char('Report File Name Pattern', translate=True,
        help='By default, the file name is generated from the report name and '
        'the record’s full name. To customize the file name, you can define a jinja2 pattern. '
        'Eg. {{ record.render.rec_name }}-{{ record.render.id }}')

    @classmethod
    def __setup__(cls):
        super(ActionReport, cls).__setup__()

        jinja_option = ('jinja', 'Jinja')
        if jinja_option not in cls.template_extension.selection:
            cls.template_extension.selection.append(jinja_option)

    @classmethod
    def view_attributes(cls):
        return super(ActionReport, cls).view_attributes() + [
            ('//page[@id="html_report"]', 'states', {
                    'invisible': Eval('template_extension') != 'jinja',
                    })]

    def get_content(self, name):
        obj_name = name.replace('content', 'template')
        obj = getattr(self, obj_name)
        if not obj:
            return
        content = []
        for template in self.html_templates:
            if template.template_used and template.template_used.all_content:
                content.append(template.template_used.all_content or '')

        content_obj = obj.all_content.strip()
        first = content_obj.split('\n')[0]
        if first.startswith('{%') and 'extends' in first:
            last = '\n'.join(content_obj.split('\n')[1:])
        else:
            first = ''
            last = content_obj
        new_content = '\n'.join([first, self.jinja_template or '', last])
        content.append(new_content or '')
        return '\n\n'.join(content)

    @classmethod
    def validate(cls, reports):
        for report in reports:
            report.check_template_jinja()

    def check_template_jinja(self):
        if self.template_extension == 'jinja':
            return
        missing, unused = self.get_missing_unused_signatures()
        if missing:
            raise UserError(gettext('html_report.missing_signatures', {
                        'template': self.rec_name,
                        'missing': '\n'.join(sorted([x.rec_name for x in
                                    missing]))
                        }))
        if unused:
            raise UserError(gettext('html_report.unused_signatures', {
                        'template': self.rec_name,
                        'unused': '\n'.join(sorted([x.rec_name for x in
                                    unused]))
                        }))

    def get_missing_unused_signatures(self):
        existing = {x.signature for x in self.html_templates}
        required = self.required_signatures()
        missing = required - existing
        unused = existing - required
        return missing, unused

    def required_signatures(self):
        if not self.html_template:
            return set()
        signatures = {x for x in self.html_template.uses}
        for template in self.html_templates:
            if not template.template:
                continue
            signatures |= {x for x in template.template.uses}
        return signatures

    @fields.depends('html_template', 'html_templates')
    def on_change_html_template(self):
        pool = Pool()
        Template = pool.get('html.template')
        ReportTemplate = pool.get('html.report.template')

        missing, unused = self.get_missing_unused_signatures()

        templates = list(self.html_templates)
        for signature in missing:
            record = ReportTemplate()
            record.signature = signature
            implementors = Template.search([('implements', '=', signature)])
            if len(implementors) == 1:
                record.template, = implementors
            templates.append(record)

        self.html_templates = templates

    @fields.depends('html_template', 'html_templates')
    def on_change_html_header_template(self):
        pool = Pool()
        Template = pool.get('html.template')
        ReportTemplate = pool.get('html.report.template')

        missing, unused = self.get_missing_unused_signatures()

        templates = list(self.html_templates)
        for signature in missing:
            record = ReportTemplate()
            record.signature = signature
            implementors = Template.search([('implements', '=', signature)])
            if len(implementors) == 1:
                record.template, = implementors
            templates.append(record)

        self.html_templates = templates

    @classmethod
    def gettext(cls, *args, **variables):
        HTMLTemplateTranslation = Pool().get('html.template.translation')

        report, src, lang = args
        key = (report, src, lang)
        text = cls._html_translation_cache.get(key)
        if text is None:
            translations = HTMLTemplateTranslation.search([
                ('report', '=', report),
                ('src', '=', src),
                ('lang', '=', lang),
                ], limit=1)
            if translations:
                translation, = translations
                text = translation.value or translation.src
            else:
                parent_lang = get_parent_language(lang)

                translations = HTMLTemplateTranslation.search([
                    ('report', '=', report),
                    ('src', '=', src),
                    ('lang', '=', parent_lang),
                    ], limit=1)
                if translations:
                    translation, = translations
                    text = translation.value or translation.src
                else:
                    text = src
            cls._html_translation_cache.set(key, text)
        return text if not variables else text % variables


class HTMLTemplateTranslation(ModelSQL, ModelView):
    'HTML Template Translation'
    __name__ = 'html.template.translation'
    _order_name = 'src'
    report = fields.Many2One('ir.action.report', 'Report', required=True,
        ondelete='CASCADE')
    src = fields.Text('Source', required=True)
    value = fields.Text('Translation Value')
    lang = fields.Selection('get_language', string='Language', required=True)
    _get_language_cache = Cache('html.template.translation.get_language')

    @classmethod
    def get_language(cls):
        result = cls._get_language_cache.get(None)
        if result is not None:
            return result
        pool = Pool()
        Lang = pool.get('ir.lang')
        langs = Lang.search([])
        result = [(lang.code, lang.name) for lang in langs]
        cls._get_language_cache.set(None, result)
        return result

    @classmethod
    def create(cls, vlist):
        Report = Pool().get('ir.action.report')
        Report._html_translation_cache.clear()
        return super(HTMLTemplateTranslation, cls).create(vlist)

    @classmethod
    def write(cls, *args):
        Report = Pool().get('ir.action.report')
        Report._html_translation_cache.clear()
        return super(HTMLTemplateTranslation, cls).write(*args)

    @classmethod
    def delete(cls, translations):
        Report = Pool().get('ir.action.report')
        Report._html_translation_cache.clear()
        return super(HTMLTemplateTranslation, cls).delete(translations)

    @property
    def unique_key(self):
        return (self.src, self.lang)
