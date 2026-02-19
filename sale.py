from trytond.pool import Pool, PoolMeta
from trytond.i18n import gettext
from trytond.pyson import Eval
from trytond.modules.html_report.template import HTMLPartyInfoMixin
from trytond.modules.html_report.engine import HTMLReportMixin
from trytond.modules.html_report.dominate_report import DominateReportMixin
from trytond.modules.html_report.discount import HTMLDiscountReportMixin
from dominate.util import raw
from dominate.tags import (div, footer as footer_tag, h1, h2, h3, h4,
    header as header_tag, img, link, p, strong, table, tbody, td, th, thead, tr)


class Sale(HTMLPartyInfoMixin, HTMLReportMixin, metaclass=PoolMeta):
    __name__ = 'sale.sale'

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls.html_party.context = {'company': Eval('company', -1)}
        cls.html_party.depends = ['company']

    def get_html_address(self, name):
        return (self.invoice_address and self.invoice_address.id
            or super().get_html_address(name))

    def get_html_second_address(self, name):
        return (self.shipment_address and self.shipment_address.id
            or super().get_html_second_address(name))

    def get_html_second_address_label(self, name):
        pool = Pool()
        Report = pool.get('sale.sale')
        return Report.label(self.__name__, 'shipment_address')


class SaleLineDiscount(HTMLDiscountReportMixin, metaclass=PoolMeta):
    __name__ = 'sale.line'


class SaleReport(DominateReportMixin, metaclass=PoolMeta):
    __name__ = 'sale.sale'

    @classmethod
    def show_company_info(cls, company, show_party=True,
            show_contact_mechanism=True):
        return company.raw.__class__.show_company_info(
            company, show_party=show_party,
            show_contact_mechanism=show_contact_mechanism)

    @classmethod
    def show_party_info(cls, party, tax_identifier, address,
            second_address_label, second_address):
        return party.raw.show_party_info(
            tax_identifier, address, second_address_label, second_address)

    @classmethod
    def show_footer(cls, company=None):
        if company is None:
            return raw('')
        return company.raw.__class__.show_footer(company)

    @classmethod
    def show_payment_info(cls, document):
        return document.company.raw.__class__.show_payment_info(document)

    @classmethod
    def show_totals(cls, record):
        return record.company.raw.__class__.show_totals(record)

    @classmethod
    def _show_sale_lines(cls, document):
        lines_table = table(style='width:100%;')
        with lines_table:
            with thead():
                with tr():
                    th(cls.label('product.product', 'code'),
                        nowrap=True)
                    th(cls.label('product.template', 'name'),
                        nowrap=True)
                    th(cls.label('sale.line', 'quantity'),
                        cls='text-right', nowrap=True)
                    th(cls.label('sale.line', 'unit_price'),
                        cls='text-right', nowrap=True)
                    th('')
                    th(cls.label('sale.line', 'amount'),
                        cls='text-right', nowrap=True)
            with tbody(cls='border'):
                for line in document.lines:
                    if line.raw.type == 'line':
                        with tr():
                            if line.raw.description:
                                td(raw(line.render.description), colspan='2')
                            else:
                                td(line.product and line.product.render.code or '-')
                                td(line.product and line.product.render.name or '-')
                            qty = '%s' % line.render.quantity
                            if line.unit:
                                qty += ' %s' % line.unit.render.symbol
                            td(qty, cls='text-right')
                            base_price = getattr(line.raw, 'base_price', None)
                            discount = getattr(line.raw, 'discount', None)
                            if base_price:
                                td('%s %s' % (
                                    line.render.base_price,
                                    line.sale.currency.render.symbol),
                                    cls='text-right')
                                if discount:
                                    td(line.render.discount, cls='text-right')
                                else:
                                    td(' ')
                            else:
                                td('%s %s' % (
                                    line.render.unit_price,
                                    line.sale.currency.render.symbol),
                                    cls='text-right')
                                td('')
                            td('%s %s' % (
                                line.render.amount,
                                line.sale.currency.render.symbol),
                                cls='text-right')
                    elif line.raw.type == 'comment':
                        with tr():
                            td(line.render.type)
                            td(raw(line.render.description), colspan='5')
                    elif line.raw.type == 'title':
                        with tr():
                            with td(colspan='6'):
                                strong(line.render.description)
                    elif line.raw.type == 'subtotal':
                        with tr():
                            with td(colspan='5'):
                                strong(line.render.description)
                            with td(cls='text-right'):
                                strong('%s %s' % (
                                    line.render.amount,
                                    line.sale.currency.render.symbol))
        return lines_table

    @classmethod
    def _document_info(cls, record, is_proforma=False):
        if is_proforma:
            title = gettext('Proforma')
        else:
            if record.raw.state in ('quotation', 'draft'):
                title = record.render.state
            else:
                title = cls.label(record.raw.__name__)

        document_date = record.raw.sale_date and record.render.sale_date or ''
        label_date = cls.label(record.raw.__name__, 'sale_date')

        container = div()
        with container:
            h1('%s: %s' % (title, record.render.number
                if record.raw.number else ''), cls='document')
            if document_date:
                h2('%s: %s' % (label_date, document_date), cls='document')
            if record.raw.reference:
                h2('%s: %s' % (
                    cls.label(record.raw.__name__, 'reference'),
                    record.render.reference), cls='document')
            if getattr(record.raw, 'carrier', None) and not is_proforma:
                h3('%s: %s' % (
                    cls.label(record.raw.__name__, 'carrier'),
                    record.carrier.party.render.name), cls='document')
        return container

    @classmethod
    def header(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        company = record.company
        is_proforma = action and action.name == 'Proforma'

        header = div()
        with header:
            link(rel='stylesheet', href=cls._base_css_href())
            with header_tag(id='header'):
                with table():
                    with tr():
                        with td():
                            if company.render.logo:
                                img(cls='logo', src=company.render.logo)
                        with td():
                            cls._document_info(record, is_proforma=is_proforma)
                    with tr():
                        with td(cls='party_info'):
                            cls.show_company_info(company)
                        with td(cls='party_info'):
                            party = record.html_party
                            tax_identifier = record.html_tax_identifier
                            address = record.html_address
                            second_address_label = record.html_address
                            second_address = record.html_address
                            cls.show_party_info(party, tax_identifier, address,
                                second_address_label, second_address)
        return header

    @classmethod
    def footer(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        company = record.company
        footer = div()
        with footer:
            link(rel='stylesheet', href=cls._base_css_href())
            with footer_tag(id='footer', align='center'):
                cls.show_footer(company)
        return footer

    @classmethod
    def last_footer(cls, action, record=None, records=None,
            data=None):
        if record is None and records:
            record = records[0]
        last_footer = div()
        with last_footer:
            link(rel='stylesheet', href=cls._base_css_href())
            with div(
                    id='last-footer',
                    align='center',
                    style=('position: fixed; width: 16cm; bottom: 0;'
                        ' padding: 0.1cm; margin-left: 2cm;'
                        ' margin-right: 2cm; margin-bottom: 2cm;')):
                with table(id='totals', cls='condensed'):
                    with tr():
                        with td():
                            cls.show_payment_info(record)
                        with td():
                            cls.show_totals(record)
        return last_footer

    @classmethod
    def title(cls, action, record=None, records=None, data=None):
        return cls.label('sale.sale')

    @classmethod
    def body(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        container = div()
        with container:
            container.add(cls._show_sale_lines(record))
            if record.raw.comment:
                h4(cls.label('sale.sale', 'comment'))
                p(raw(record.render.comment))

        return container
