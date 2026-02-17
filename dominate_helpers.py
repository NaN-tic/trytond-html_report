import os

from dominate import document
from dominate.util import raw
from dominate.tags import body as body_tag, link, meta, style

from trytond.pool import Pool
from trytond.tools import file_open


def _module_path(name):
    module, path = name.split('/', 1)
    with file_open(os.path.join(module, path)) as f:
        return 'file://' + f.name


def _base_css_href():
    return _module_path('html_report/templates/base.css')


def _css_extension(action):
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


def _css_override(action):
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


def build_document(action, title, body_nodes):
    doc = document(title=title)
    doc['lang'] = 'en'
    with doc.head:
        meta(charset='utf-8')
        meta(name='description', content='')
        meta(name='author', content='Nantic')
        css_override = _css_override(action)
        if css_override:
            style(raw(css_override))
        else:
            link(rel='stylesheet', href=_base_css_href(), type='text/css')
        css_ext = _css_extension(action)
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
