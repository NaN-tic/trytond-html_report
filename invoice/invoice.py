from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.rpc import RPC
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.modules.html_report.html import HTMLPartyInfoMixin
from trytond.modules.html_report.engine import HTMLReportMixin


class Invoice(HTMLPartyInfoMixin, metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls.html_party.context = {'company': Eval('company', -1)}
        cls.html_party.depends = ['company']

    def get_html_address(self, name):
        return (self.invoice_address and self.invoice_address.id
            or super().get_html_address(name))


class InvoiceLine(metaclass=PoolMeta):
    __name__ = 'account.invoice.line'
    shipment_key = fields.Function(fields.Char("Shipment Key",
        ), 'get_shipment_key')
    origin_line_key = fields.Function(fields.Char("Origin Line Key",
        ), 'get_origin_line_key')

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


class InvoiceReport(HTMLReportMixin, metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def _execute_html_report(cls, records, data, action, side_margin=2,
            extra_vertical_margin=30):

        pool = Pool()
        Invoice = pool.get('account.invoice')

        # Re-instantiate because records are DualRecord
        invoice, = Invoice.browse([r.raw.id for r in records])
        if invoice.invoice_report_cache:
            return (
                invoice.invoice_report_format,
                invoice.invoice_report_cache)

        extension, document = super()._execute_html_report(records, data, action,
                side_margin, extra_vertical_margin)

        # If the invoice is posted or paid and the report not saved in
        # invoice_report_cache there was an error somewhere. So we save it
        # now in invoice_report_cache
        if invoice.state in {'posted', 'paid'} and invoice.type == 'out':
            if isinstance(data, str):
                data = bytes(data, 'utf-8')
            invoice.invoice_report_format = extension
            invoice.invoice_report_cache = \
                Invoice.invoice_report_cache.cast(document)
            invoice.save()

        return extension, document
