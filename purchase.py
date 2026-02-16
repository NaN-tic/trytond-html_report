from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.modules.html_report.template import HTMLPartyInfoMixin
from trytond.modules.html_report.discount import HTMLDiscountReportMixin
from trytond.modules.html_report.engine import HTMLReportMixin
from trytond.modules.html_report.dominate_report import DominateReportMixin
from trytond.modules.html_report import dominate_helpers as dh
from dominate.util import raw
from dominate.tags import (div, footer as footer_tag, h1, h2, h4,
    header as header_tag, img, link, p, strong, table, tbody, td, th, thead, tr)


class Purchase(HTMLPartyInfoMixin, metaclass=PoolMeta):
    __name__ = 'purchase.purchase'

    @classmethod
    def __setup__(cls):
        super(Purchase, cls).__setup__()
        cls.html_party.context = {'company': Eval('company', -1)}
        cls.html_party.depends = ['company']

    def get_html_address(self, name):
        return (self.invoice_address and self.invoice_address.id
            or super().get_html_address(name))


class PurchaseLineDiscount(HTMLDiscountReportMixin, metaclass=PoolMeta):
    __name__ = 'purchase.line'


class PurchaseReport(DominateReportMixin, metaclass=PoolMeta):
    __name__ = 'purchase.purchase'

    @classmethod
    def _show_purchase_lines(cls, document, simplified=False):
        lines_table = table(style='width:100%;')
        with lines_table:
            with thead():
                with tr():
                    th(HTMLReportMixin.label('product.product', 'code'),
                        nowrap=True)
                    th(HTMLReportMixin.label('product.template', 'name'),
                        nowrap=True)
                    th(HTMLReportMixin.label('purchase.line', 'quantity'),
                        cls='text-right', nowrap=True)
                    if not simplified:
                        th(HTMLReportMixin.label('purchase.line', 'unit_price'),
                            cls='text-right', nowrap=True)
                        th('')
                        th(HTMLReportMixin.label('purchase.line', 'amount'),
                            cls='text-right', nowrap=True)
            with tbody(cls='border'):
                for line in document.lines:
                    if line.raw.type == 'line':
                        with tr():
                            if line.raw.description:
                                td(raw(line.render.description), colspan='2')
                            elif line.raw.product_supplier and line.product_supplier.raw.name:
                                td(line.product_supplier.render.code or '-')
                                td(line.product_supplier.render.name or '-')
                            elif line.raw.product:
                                td(line.product and line.product.render.code or '-')
                                td(line.product and line.product.render.name or '-')

                            qty = '%s' % line.render.quantity
                            if line.unit and line.unit.render.symbol:
                                qty += ' %s' % line.unit.render.symbol
                            td(qty, cls='text-right')

                            if not simplified:
                                base_price = getattr(line.raw, 'base_price', None)
                                discount = getattr(line.raw, 'discount', None)
                                if base_price:
                                    td('%s %s' % (
                                        line.render.base_price,
                                        line.purchase.currency.render.symbol),
                                        cls='text-right')
                                    if discount:
                                        td(line.render.discount, cls='text-right')
                                    else:
                                        td(' ')
                                else:
                                    td('%s %s' % (
                                        line.render.unit_price,
                                        line.purchase.currency.render.symbol),
                                        cls='text-right')
                                    td('')
                                td('%s %s' % (
                                    line.render.amount,
                                    line.purchase.currency.render.symbol),
                                    cls='text-right')
                    elif line.raw.type == 'comment':
                        with tr():
                            td(line.render.type)
                            td(raw(line.render.description),
                                colspan='2' if simplified else '5')
                    elif line.raw.type == 'title':
                        with tr():
                            with td(colspan='3' if simplified else '6'):
                                strong(line.render.description)
                    elif line.raw.type == 'subtotal' and not simplified:
                        with tr():
                            with td(colspan='5'):
                                strong(line.render.description)
                            with td(cls='text-right'):
                                strong('%s %s' % (
                                    line.render.amount,
                                    line.purchase.currency.render.symbol))
        return lines_table

    @classmethod
    def _document_info(cls, record):
        if record.raw.state in ('quotation', 'draft'):
            title = record.render.state
        else:
            title = HTMLReportMixin.label(record.raw.__name__)

        document_date = record.raw.purchase_date and record.render.purchase_date or ''
        label_date = HTMLReportMixin.label(record.raw.__name__, 'purchase_date')

        container = div()
        with container:
            h1('%s: %s' % (title, record.render.number
                if record.raw.number else ''), cls='document')
            if document_date:
                h2('%s: %s' % (label_date, document_date), cls='document')
            if record.raw.reference:
                h2('%s: %s' % (
                    HTMLReportMixin.label(record.raw.__name__, 'reference'),
                    record.render.reference), cls='document')
        return container

    @classmethod
    def header(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        company = record.company
        header = div()
        with header:
            link(rel='stylesheet', href=dh._base_css_href())
            with header_tag(id='header'):
                with table():
                    with tr():
                        with td():
                            if company.render.logo:
                                img(cls='logo', src=company.render.logo)
                        with td():
                            cls._document_info(record)
                    with tr():
                        with td(cls='party_info'):
                            dh.show_company_info(company)
                        with td(cls='party_info'):
                            party = record.html_party
                            tax_identifier = record.html_tax_identifier
                            address = record.html_address
                            second_address_label = record.html_address
                            second_address = record.html_address
                            dh.show_party_info(party, tax_identifier, address,
                                second_address_label, second_address)
        return header

    @classmethod
    def footer(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        footer = div()
        with footer:
            link(rel='stylesheet', href=dh._base_css_href())
            with footer_tag(id='footer', align='center'):
                dh.show_footer()
        return footer

    @classmethod
    def last_footer(cls, action, record=None, records=None,
            data=None):
        if record is None and records:
            record = records[0]
        simplified = action and 'simplified' in action.report_name
        last_footer = div()
        with last_footer:
            link(rel='stylesheet', href=dh._base_css_href())
            with div(
                    id='last-footer',
                    align='center',
                    style=('position: fixed; width: 16cm; bottom: 0;'
                        ' padding: 0.1cm; margin-left: 2cm;'
                        ' margin-right: 2cm; margin-bottom: 2cm;')):
                with table(id='totals', cls='condensed'):
                    with tr():
                        with td():
                            dh.show_payment_info(record)
                        with td():
                            if not simplified:
                                dh.show_totals(record)
        return last_footer

    @classmethod
    def main(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        simplified = action and 'simplified' in action.report_name
        body_nodes = []
        body_nodes.append(cls._show_purchase_lines(record,
            simplified=simplified))
        if record.raw.comment:
            body_nodes.append(h4(HTMLReportMixin.label(
                'purchase.purchase', 'comment')))
            body_nodes.append(p(raw(record.render.comment)))

        title = HTMLReportMixin.label('purchase.purchase')
        return dh.build_document(action, title, body_nodes)


class PurchaseSimplifiedReport(DominateReportMixin, metaclass=PoolMeta):
    __name__ = 'purchase.purchase.simplified'

    @classmethod
    def main(cls, action, record=None, records=None, data=None):
        return PurchaseReport.main(action, record=record,
            records=records, data=data)

    @classmethod
    def header(cls, action, record=None, records=None, data=None):
        return PurchaseReport.header(action, record=record,
            records=records, data=data)

    @classmethod
    def footer(cls, action, record=None, records=None, data=None):
        return PurchaseReport.footer(action, record=record,
            records=records, data=data)

    @classmethod
    def last_footer(cls, action, record=None, records=None, data=None):
        return PurchaseReport.last_footer(action, record=record,
            records=records, data=data)
