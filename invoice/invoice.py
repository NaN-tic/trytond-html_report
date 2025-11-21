from collections import defaultdict
from decimal import Decimal
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.modules.html_report.template import HTMLPartyInfoMixin
from trytond.modules.html_report.engine import DualRecord, HTMLReportMixin
from trytond.modules.html_report.discount import HTMLDiscountReportMixin


class Invoice(HTMLPartyInfoMixin, metaclass=PoolMeta):
    __name__ = 'account.invoice'
    html_lines_to_pay = fields.Function(fields.Many2Many(
            'account.move.line', None, None, 'HTML Lines to Pay'),
        'get_html_lines_to_pay')

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls.html_party.context = {'company': Eval('company', -1)}
        cls.html_party.depends = ['company']

    def get_html_address(self, name):
        return (self.invoice_address and self.invoice_address.id
            or super().get_html_address(name))

    @classmethod
    def get_html_lines_to_pay(cls, invoices, name):
        lines = defaultdict(list)
        for invoice in invoices:
            lines[invoice.id] = [l.id for l in sorted([line for line in invoice.lines_to_pay
                if not line.reconciliation and line.maturity_date],
                key=lambda x: x.maturity_date)]
        return lines

    @property
    def html_taxes(self):
        currency_digits = self.currency.digits
        precision = '0.' + '0' * currency_digits if currency_digits > 0 else '0'

        def default_amount():
            return {'base': Decimal(precision), 'amount': Decimal(precision)}

        taxes = defaultdict(default_amount)
        for tax in self.taxes:
            taxes[tax.tax]['base'] += tax.base
            taxes[tax.tax]['amount'] += tax.amount
            taxes[tax.tax]['legal_notice'] = tax.legal_notice
        return {DualRecord(k): v for k, v in taxes.items()}


class InvoiceLine(metaclass=PoolMeta):
    __name__ = 'account.invoice.line'
    shipment_key = fields.Function(fields.Char("Shipment Key",
        ), 'get_shipment_key')
    origin_line_key = fields.Function(fields.Char("Origin Line Key",
        ), 'get_origin_line_key')
    html_product_code = fields.Function(fields.Char(
        "HTML Code"), 'get_html_product_code')

    @classmethod
    def _get_shipment_origin(cls):
        return ['stock.shipment.out', 'stock.shipment.out.return',
            'stock.shipment.in', 'stock.shipment.in.return',
            'stock.shipment.drop']

    def get_shipment_key(self, name):
        if not hasattr(self, 'stock_moves'):
            return ''
        if not self.stock_moves:
            return ''
        shipment = self.stock_moves[0].shipment
        if not shipment:
            return ''
        return str(shipment)

    @classmethod
    def _get_origin_line_keys(cls):
        return {
            'sale.line': 'sale',
            'purchase.line': 'purchase',
            }

    def get_origin_line_key(self, name):
        models = self._get_origin_line_keys()
        if self.origin:
            model = self.origin.__name__
            if models.get(model):
                field = models.get(model)
                return str(getattr(self.origin, field))
        return ''

    def get_html_product_code(self, name):
        return self.product and self.product.code or ''


class InvoiceLineDiscount(HTMLDiscountReportMixin, metaclass=PoolMeta):
    __name__ = 'account.invoice.line'


class InvoiceReport(HTMLReportMixin, metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def _execute_html_report(cls, records, data, action, side_margin=2,
            extra_vertical_margin=30):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        Configuration = Pool().get('account.configuration')

        config = Configuration(1)
        extension, document = None, None
        is_html = Transaction().context.get('output_format') == 'html'

        to_invoice_cache = {}
        if config.use_invoice_report_cache:
            to_cache = [r for r in records
                            if r.raw.state in {'posted', 'paid'}
                            and r.raw.type == 'out'
                            and not r.raw.invoice_report_cache]

            for record in to_cache:
                extension, document = super()._execute_html_report([record], data, action,
                        side_margin, extra_vertical_margin)

                if isinstance(document, str):
                    document = bytes(document, 'utf-8')

                to_invoice_cache[record.raw.id] = {
                    'invoice_report_format': extension,
                    'invoice_report_cache': Invoice.invoice_report_cache.cast(document),
                    }

        # Check if the transaction is readonly or is_html
        if to_invoice_cache and not is_html and not Transaction().readonly:
            to_write = []
            for id, values in to_invoice_cache.items():
                # Re-instantiate because records are DualRecord
                to_write.extend(([Invoice(id)], {
                    'invoice_report_format': values['invoice_report_format'],
                    'invoice_report_cache': values['invoice_report_cache'],
                    }))
            Invoice.write(*to_write)

        documents = []
        for record in records:
            if to_invoice_cache.get(record.raw.id):
                extension = to_invoice_cache[record.raw.id]['invoice_report_format']
                document = to_invoice_cache[record.raw.id]['invoice_report_cache']
                documents.append(document)
            elif record.raw.invoice_report_cache:
                extension = record.raw.invoice_report_format
                document = record.raw.invoice_report_cache
                documents.append(document)
            else:
                extension, document = super()._execute_html_report([record], data, action,
                    side_margin, extra_vertical_margin)
                documents.append(document)
        if len(documents) > 1 and not is_html:
            extension = 'pdf'
            document = cls.merge_pdfs(documents)

        return extension, document
