from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.modules.html_report.template import HTMLPartyInfoMixin
from trytond.modules.html_report.engine import HTMLReportMixin


class ShipmentOutReturn(HTMLPartyInfoMixin, HTMLReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.shipment.out.return'
    show_lots = fields.Function(fields.Boolean('Show Lots'),
        'get_show_lots')

    @classmethod
    def __setup__(cls):
        super(ShipmentOutReturn, cls).__setup__()
        cls.html_party.context = {'company': Eval('company', -1)}
        cls.html_party.depends = ['company']

    def get_show_lots(self, name):
        for move in self.incoming_moves:
            if hasattr(move, 'lot') and getattr(move, 'lot'):
                return True
        return False

    def get_html_party(self, name):
        return self.customer and self.customer.id

    def get_html_second_address(self, name):
        return self.contact_address and self.contact_address.id

    def get_html_second_address_label(self, name):
        pool = Pool()
        Report = pool.get('stock.shipment.out.return')
        return Report.label(self.__name__, "contact_address")


class ShipmentIn(HTMLReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.shipment.in'
    show_lots = fields.Function(fields.Boolean('Show Lots'),
        'get_show_lots')

    def get_show_lots(self, name):
        for move in self.moves:
            if hasattr(move, 'lot') and getattr(move, 'lot'):
                return True
        return False


class ShipmentInReturn(HTMLPartyInfoMixin, HTMLReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.shipment.in.return'
    show_lots = fields.Function(fields.Boolean('Show Lots'),
        'get_show_lots')

    @classmethod
    def __setup__(cls):
        super(ShipmentInReturn, cls).__setup__()
        cls.html_party.context = {'company': Eval('company', -1)}
        cls.html_party.depends = ['company']

    def get_show_lots(self, name):
        for move in self.moves:
            if hasattr(move, 'lot') and getattr(move, 'lot'):
                return True
        return False

    def get_html_party(self, name):
        return self.supplier and self.supplier.id

    def get_html_second_address(self, name):
        return self.delivery_address and self.delivery_address.id

    def get_html_second_address_label(self, name):
        pool = Pool()
        Report = pool.get('stock.shipment.in.return')
        return Report.label(self.__name__, "delivery_address")


class ShipmentOut(HTMLPartyInfoMixin, HTMLReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.shipment.out'
    sorted_lines = fields.Function(fields.One2Many('stock.move',
        'line', 'Sorted Lines'), 'get_sorted_lines')
    sorted_keys = fields.Function(fields.Char('key'), 'get_sorted_keys')
    show_lots = fields.Function(fields.Boolean('Show Lots'),
        'get_show_lots')

    @classmethod
    def __setup__(cls):
        super(ShipmentOut, cls).__setup__()
        cls.html_party.context = {'company': Eval('company', -1)}
        cls.html_party.depends = ['company']

    def get_html_party(self, name):
        return self.customer and self.customer.id

    def get_html_address(self, name):
        return self.delivery_address and self.delivery_address.id

    def get_html_second_address(self, name):
        return self.delivery_address and self.delivery_address.id

    def get_html_second_address_label(self, name):
        pool = Pool()
        Report = pool.get('stock.shipment.out')
        return Report.label(self.__name__, "delivery_address")

    def get_sorted_lines(self, name):
        lines = [x for x in self.outgoing_moves]
        lines.sort(key=lambda k: k.sort_key, reverse=True)
        return [x.id for x in lines]

    def get_sorted_keys(self, name):
        keys = []
        for x in self.sorted_lines:
            if x.sort_key in keys:
                continue
            keys.append(x.sort_key)
        return keys

    def get_show_lots(self, name):
        for move in self.inventory_moves or self.outgoing_moves:
            if hasattr(move, 'lot') and getattr(move, 'lot'):
                return True
        return False


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

    sort_key = fields.Function(fields.Char('key'), 'get_sorted_key')
    origin_key = fields.Function(fields.Char("Origin Key",
        ), 'get_origin_key')

    def get_sorted_key(self, name):
        pool = Pool()
        ShipmentOut = pool.get('stock.shipment.out')
        ShipmentIn = pool.get('stock.shipment.in')

        key = []
        if self.shipment and isinstance(self.shipment, ShipmentOut):
            if self.shipment.warehouse_storage == self.shipment.warehouse_output:
                sale = (self.origin
                        and ('sale.line' in str(self.origin))
                        and self.origin.sale or None)
            else:
                sale = (self.origin
                        and ('sale.line' in str(self.origin))
                        and self.origin.sale or None)
            if sale and sale not in key:
                key.append(sale)

        elif self.shipment and isinstance(self.shipment, ShipmentIn):
            if self.origin and 'purchase.line' in str(self.origin):
                purchase = self.origin.purchase
                if purchase in key:
                    key.append(purchase)
        return key

    def get_origin_key(self, name):
        Move = Pool().get('stock.move')

        origin = self.origin
        if self.shipment and origin and isinstance(origin, Move):
            if origin.origin:
                origin = origin.origin
        if origin and hasattr(origin, 'document_origin') and origin.document_origin:
            origin = origin.document_origin
        return str(origin) if origin is not None else ''


class ShipmentInternal(HTMLPartyInfoMixin, metaclass=PoolMeta):
    __name__ = 'stock.shipment.internal'

    @classmethod
    def __setup__(cls):
        super(ShipmentInternal, cls).__setup__()
        cls.html_party.context = {'company': Eval('company', -1)}
        cls.html_party.depends = ['company']

    def get_html_party(self, name):
        return


class StockInventory(HTMLReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.inventory'
