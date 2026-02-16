import os

from dominate import document
from dominate.util import raw
from dominate.tags import (b, body as body_tag, br, div, hr, img, link, meta,
    span, strong, style, table, td, th, tr)

from trytond.pool import Pool
from trytond.tools import file_open
from .engine import HTMLReportMixin


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


def show_image(image_class, image):
    if not image:
        return raw('')
    return img(cls=image_class, src=image)


def show_footer():
    return raw('<p align="center"> </p>')


def show_company_info(company, show_party=True, show_contact_mechanism=True):
    party = company.party
    address = party.addresses and party.addresses[0] or None
    tax_identifier = party.tax_identifier

    container = div(id='company-info', cls='header-details')
    if show_party:
        with container:
            span(company.party.render.name, cls='company-info-name')
            br()
    if tax_identifier:
        with container:
            raw(tax_identifier.render.code)
            br()
    if address:
        with container:
            with div(cls='company-info-address'):
                raw(address.render.full_address.replace('\n', '<br/>'))
    if show_contact_mechanism:
        with container:
            with div(cls='company-info-contact-mechanims'):
                if party.raw.phone:
                    raw('%s: %s' % (
                        HTMLReportMixin.label('party.party', 'phone'),
                        party.render.phone))
                    br()
                if party.raw.email:
                    raw(party.render.email)
                    br()
                if party.raw.website:
                    raw(party.render.website)
    return container


def show_party_info(party, tax_identifier, address, second_address_label,
        second_address):
    if not party:
        return raw('')
    container = div()
    with container:
        b(party.render.name)
        br()
        if tax_identifier:
            raw(tax_identifier.render.code)
            br()
        if address:
            raw(address.render.full_address.replace('\n', '<br/>'))
        br()
        if party.raw.phone:
            raw('%s: %s' % (
                HTMLReportMixin.label('party.party', 'phone'),
                party.render.phone))
            br()
        if party.raw.email:
            raw(party.render.email)
            br()
        if second_address and address and second_address.raw.id != address.raw.id:
            if second_address_label:
                strong(' %s' % second_address_label)
                br()
            raw(second_address.render.full_address.replace('\n', '<br/>'))
    return container


def show_payment_info(document):
    container = div()
    with container:
        if getattr(document.raw, 'payment_term', None):
            strong('%s: ' % HTMLReportMixin.label(
                document.raw.__name__, 'payment_term'))
            raw(document.payment_term.render.name)
            br()
        if getattr(document.raw, 'payment_type', None):
            strong('%s: ' % HTMLReportMixin.label(
                document.raw.__name__, 'payment_type'))
            raw(document.payment_type.render.name)
            br()
        if getattr(document.raw, 'bank_account', None):
            strong('%s: ' % HTMLReportMixin.label(
                document.raw.__name__, 'bank_account'))
            raw(document.bank_account.render.rec_name)
            if (document.bank_account.bank
                    and document.bank_account.bank.raw.bic):
                raw(' (%s)' % document.bank_account.bank.render.bic)
            br()
        strong('%s:' % HTMLReportMixin.label(
            document.raw.__name__, 'currency'))
        raw(' %s' % document.currency.render.name)
        if getattr(document.raw, 'different_currencies', None):
            strong('%s:' % HTMLReportMixin.label(
                document.raw.__name__, 'currency'))
            raw(' %s' % document.company.currency.render.name)
            strong('%s:' % HTMLReportMixin.label(
                document.raw.__name__, 'company_untaxed_amount'))
            raw(' %s' % document.render.company_untaxed_amount)
            strong('%s:' % HTMLReportMixin.label(
                document.raw.__name__, 'company_tax_amount'))
            raw(' %s' % document.render.company_tax_amount)
            strong('%s:' % HTMLReportMixin.label(
                document.raw.__name__, 'company_total_amount'))
            raw(' %s' % document.render.company_total_amount)
    return container


def show_totals(record):
    totals_table = table(id='totals')
    with totals_table:
        with tr():
            th('%s:' % HTMLReportMixin.label(record.raw.__name__,
                'untaxed_amount'), scope='row',
                cls='text-right total-label total-luntaxed')
            td('%s %s' % (record.render.untaxed_amount,
                record.currency.render.symbol),
                cls='text-right total-value total-vuntaxed')
        with tr():
            th('%s:' % HTMLReportMixin.label(record.raw.__name__,
                'tax_amount'), scope='row',
                cls='text-right total-label total-ltax')
            td('%s %s' % (record.render.tax_amount,
                record.currency.render.symbol),
                cls='text-right total-value total-vtax')
        with tr():
            th('%s:' % HTMLReportMixin.label(record.raw.__name__,
                'total_amount'), scope='row',
                cls='text-right total-label total-lamount')
            td('%s %s' % (record.render.total_amount,
                record.currency.render.symbol),
                cls='text-right total-value total-vamount')
    return totals_table


def show_totals_horizontal(record):
    totals_table = table(id='totals')
    with totals_table:
        with tr():
            th(HTMLReportMixin.label(record.raw.__name__, 'untaxed_amount'),
                cls='text-center upper total-label total-luntaxed')
            th(HTMLReportMixin.label(record.raw.__name__, 'tax_amount'),
                cls='text-center upper total-label total-ltax')
            th(HTMLReportMixin.label(record.raw.__name__, 'total_amount'),
                cls='text-center upper total-label total-lamount')
        with tr():
            td('%s %s' % (record.render.untaxed_amount,
                record.currency.render.symbol),
                cls='text-center total-value total-vuntaxed')
            td('%s %s' % (record.render.tax_amount,
                record.currency.render.symbol),
                cls='text-center total-value total-vtax')
            td('%s %s' % (record.render.total_amount,
                record.currency.render.symbol),
                cls='text-center total-value total-vamount')
        tr()
    return totals_table


def show_simplified_hr():
    container = div(cls='container')
    with container:
        div(cls='col-xs-4')
        with div(cls='col-xs-5 simplified'):
            hr(style='margin: 0px;')
    return container


def show_carrier(carrier):
    container = div()
    with container:
        raw(carrier.party.render.name)
        br()
        if carrier.party.raw.tax_identifier:
            raw(carrier.party.tax_identifier.render.code)
    return container
