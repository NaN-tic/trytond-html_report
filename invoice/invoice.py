from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.rpc import RPC
from trytond.transaction import Transaction
from trytond.modules.html_report.html import HTMLPartyInfoMixin
from trytond.modules.html_report.html_report import HTMLReport


class Invoice(HTMLPartyInfoMixin, metaclass=PoolMeta):
    __name__ = 'account.invoice'

    def get_html_address(self, name):
        return (self.invoice_address and self.invoice_address.id
            or super().get_html_address(name))


class InvoiceLine(metaclass=PoolMeta):
    __name__ = 'account.invoice.line'
    shipment = fields.Function(fields.Reference("Shipment",
        selection='get_shipment_origin'), 'get_shipment')
    origin_lines = fields.Function(fields.Reference("Origin Lines",
        selection='get_origin_line_models'), 'get_origin_lines')

    @classmethod
    def _get_shipment_origin(cls):
        return ['stock.shipment.out', 'stock.shipment.out.return',
            'stock.shipment.in', 'stock.shipment.in.return',
            'stock.shipment.drop']

    @classmethod
    def get_shipment_origin(cls):
        Model = Pool().get('ir.model')
        models = cls._get_shipment_origin()
        models = Model.search([
                ('model', 'in', models),
                ])
        return [(None, '')] + [(m.model, m.name) for m in models]

    def get_shipment(self, name):
        if not self.stock_moves:
            return
        shipment = self.stock_moves[0].shipment
        if not shipment:
            return
        return str(shipment)

    @classmethod
    def _get_origin_lines(cls):
        return {
            'sale.line': 'sale',
            'purchase.line': 'purchase',
            }

    @classmethod
    def get_origin_line_models(cls):
        Model = Pool().get('ir.model')
        models = cls._get_origin_lines().keys()
        models = Model.search([
                ('model', 'in', models),
                ])
        return [(None, '')] + [(m.model, m.name) for m in models]

    def get_origin_lines(self, name):
        models = self._get_origin_lines()
        if self.origin:
            model = self.origin.__name__
            if models.get(model):
                field = models.get(model)
                return str(getattr(self.origin, field))


class InvoiceReport(HTMLReport):
    __name__ = 'account.invoice'

    @classmethod
    def __setup__(cls):
        super(InvoiceReport, cls).__setup__()
        cls.__rpc__['execute'] = RPC(False)

    @classmethod
    def execute(cls, ids, data):
        pool = Pool()
        Invoice = pool.get('account.invoice')

        action, _ = cls.get_action(data)

        if len(ids) == 1:
            # Re-instantiate because records are TranslateModel
            invoice, = Invoice.browse(ids)
            if invoice.invoice_report_cache:
                return (
                    invoice.invoice_report_format,
                    bytes(invoice.invoice_report_cache),
                    cls.get_direct_print(action),
                    cls.get_name(action))

        result = super(InvoiceReport, cls).execute(ids, data)

        if (len(ids) == 1 and invoice.state in {'posted', 'paid'}
                and invoice.type == 'out'):
            with Transaction().set_context(_check_access=False):
                invoice, = Invoice.browse([invoice.id])
                format_, data = result[0], result[1]
                invoice.invoice_report_format = format_
                invoice.invoice_report_cache = \
                    Invoice.invoice_report_cache.cast(data)
                invoice.save()

        return result
