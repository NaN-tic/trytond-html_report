import hashlib
import re
from trytond.model import Model, ModelSQL, ModelView, fields, sequence_ordered
from trytond.pyson import Eval, Bool
from trytond.tools import file_open
from trytond.pool import Pool
from .engine import DualRecord, HTMLReportMixin


class Signature(ModelSQL, ModelView):
    'HTML Template Signature'
    __name__ = 'html.template.signature'
    name = fields.Char('Name', required=True)
    templates = fields.One2Many('html.template', 'implements', 'Templates')

    @classmethod
    def copy(cls, signatures, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('templates')
        return super().copy(signatures, default=default)


class Template(sequence_ordered(), ModelSQL, ModelView):
    'HTML Template'
    __name__ = 'html.template'
    name = fields.Char('Name', required=True)
    type = fields.Selection([
            ('base', 'Base'),
            ('header', 'Header'),
            ('footer', 'Footer'),
            ('extension', 'Extension'),
            ('block', 'Block'),
            ('macro', 'Macro'),
            ], 'Type', required=True)
    implements = fields.Many2One('html.template.signature', 'Signature',
        states={
            'required': Eval('type') == 'macro',
            'invisible': Eval('type') != 'macro',
            })
    uses = fields.Function(fields.Many2Many('html.template.usage', 'template',
        'signature', 'Uses'), 'get_uses')
    parent = fields.Many2One('html.template', 'Parent', domain=[
            ('type', 'in', ['base', 'extension']),
            ], states={
            'required': Eval('type') == 'extension',
            'invisible': Eval('type') != 'extension',
            })
    filename = fields.Char('Template path', states={
            'readonly': Bool(Eval('filename')),
            'invisible': ~Bool(Eval('filename')),
            })
    data = fields.Text('Content')
    content = fields.Function(fields.Text('Content', states={
            'readonly': Bool(Eval('filename')),
            }), 'get_content',
            setter='set_content')
    all_content = fields.Function(fields.Text('All Content'),
        'get_all_content')
    preview_record = fields.Reference('Preview Record',
        selection='get_preview_record')
    preview = fields.Function(fields.Binary('Preview',
            filename='preview_filename'), 'get_preview')
    preview_filename = fields.Function(fields.Char('Preview Filename'),
        'get_preview_filename')
    preview_placeholder_macros = fields.Boolean('Use Placeholder for Macros')

    @classmethod
    def __register__(cls, module_name):
        table_h = cls.__table_handler__(module_name)

        if table_h.column_exist('content'):
            table_h.column_rename('content', 'data')
        super().__register__(module_name)

    def get_content(self, name):
        if not self.filename:
            return self.data
        try:
            with file_open(self.filename, subdir='modules', mode='r',
                    encoding='utf-8') as fp:
                return fp.read()
        except IOError:
            return ''

    @classmethod
    def set_content(cls, views, name, value):
        cls.write(views, {'data': value})

    def get_uses(self, name):
        Signature = Pool().get('html.template.signature')

        res = []
        match = re.findall(r"show_.*\(", self.content or '')
        for name in match:
            res += Signature.search([('name', 'like', name + '%')])
        return [x.id for x in res]

    @classmethod
    def get_preview_record(cls):
        Model = Pool().get('ir.model')
        return [(None, '')] + Model.get_name_items()

    @fields.depends('preview_record', 'data')
    def get_preview(self, name=None):
        if self.type in ('base', 'extension'):
            preview = self.all_content
        else:
            preview = self.data

        if isinstance(self.preview_record, Model):
            macros = []
            for use in self.uses:
                if not self.preview_placeholder_macros and use.templates:
                    macros.append(use.templates[0].all_content)
                    continue
                bgcolor = hashlib.md5(use.name.encode()).hexdigest()
                bgcolor = bgcolor[:6]
                # If bgcolor is too dark, make the text white
                color = 'ffffff' if int(bgcolor, 16) < 0x888888 else '000000'
                macros.append(
                    '{%% macro %s %%}\n'
                    '<span style="background-color: #%s; color: #%s">%s</span>\n'
                    '{%% endmacro %%}' % (use.name, bgcolor, color, use.name)
                    )

            preview = '\n\n'.join(macros) + '\n\n' + preview
            record = DualRecord(self.preview_record)
            records = [record, record, record]
            try:
                preview = HTMLReportMixin.render_template_jinja(None, preview,
                    record=record, records=records)
            except Exception as e:
                preview = f'<pre>{e}</pre>'
        preview = f'<!DOCTYPE html>{preview}<html>'
        return preview.encode()

    @fields.depends('id')
    def get_preview_filename(self, name=None):
        return f'file{self.id}.html'

    def get_rec_name(self, name):
        res = self.name
        if self.implements:
            res += ' / ' + self.implements.rec_name
        return res

    def get_all_content(self, name):
        if self.type in ('base', 'header', 'footer'):
            return self.content
        elif self.type == 'extension':
            return '{%% extends "%s" %%} {# %s #}\n\n%s' % (self.parent.id,
                self.parent.name, self.content)
        elif self.type == 'macro':
            return '{%% macro %s %%}\n%s\n{%% endmacro %%}' % (
                self.implements.name, self.content)

    @classmethod
    def copy(cls, templates, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        res = []
        default.setdefault('filename', None)
        for template in templates:
            default.setdefault('data', template.all_content)
            res += super(Template, cls).copy([template], default=default)
        return res


class TemplateUsage(ModelSQL):
    'HTML Template Usage'
    __name__ = 'html.template.usage'
    template = fields.Many2One('html.template', 'Template', required=True,
        ondelete='CASCADE')
    signature = fields.Many2One('html.template.signature', 'Signature',
        required=True)


class ReportTemplate(ModelSQL, ModelView):
    'HTML Report - Template'
    __name__ = 'html.report.template'
    report = fields.Many2One('ir.action.report', 'Report', required=True,
        domain=[('template_extension', '=', 'jinja')], ondelete='CASCADE')
    signature = fields.Many2One('html.template.signature', 'Signature',
        required=True)
    template = fields.Many2One('html.template', 'Template',
        domain=[
            ('implements', '=', Eval('signature', -1)),
            ])
    template_used = fields.Function(
        fields.Many2One('html.template', 'Template Used'), 'get_template_used')

    def get_template_used(self, name):
        Template = Pool().get('html.template')
        if self.template:
            return self.template.id
        templates = Template.search([('implements', '=', self.signature)])
        if templates:
            return templates[0].id


class HTMLPartyInfoMixin:
    __slots__ = ()
    html_party = fields.Function(fields.Many2One('party.party', 'HTML Party'),
        'get_html_party')
    html_tax_identifier = fields.Function(fields.Many2One('party.identifier',
        "HTML Party Tax Identifier"), 'get_html_tax_identifier')
    html_address = fields.Function(fields.Many2One('party.address',
        'HTML Party Address'), 'get_html_address')
    html_second_address = fields.Function(fields.Many2One('party.address',
        'HTML Second Address'), 'get_html_second_address')
    html_second_address_label = fields.Function(fields.Char(
        'HTML Second Address Label'), 'get_html_second_address_label')

    def get_html_party(self, name):
        return self.party and self.party.id

    def get_html_tax_identifier(self, name):
        return (self.html_party and self.html_party.tax_identifier
            and self.html_party.tax_identifier.id)

    def get_html_address(self, name):
        return (self.html_party and self.html_party.addresses
            and self.html_party.addresses[0].id or None)

    def get_html_second_address(self, name):
        return

    def get_html_second_address_label(self, name):
        return
