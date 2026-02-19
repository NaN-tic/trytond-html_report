from dominate.util import raw
from dominate.tags import (br, div, footer as footer_tag, h1, h2, h3, h4,
    header as header_tag, img, link, p, strong, table, tbody, td, th, thead, tr)

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.modules.html_report.template import HTMLPartyInfoMixin
from trytond.modules.html_report.engine import DualRecord, HTMLReportMixin
from trytond.modules.html_report.dominate_report import DominateReportMixin
from trytond.modules.html_report.discount import HTMLDiscountReportMixin


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
    sorted_lines = fields.Function(fields.Many2Many('stock.move', None, None,
        'Sorted Lines'), 'get_sorted_lines')
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

    @property
    def sorted_keys(self):
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
    origin_key = fields.Function(fields.Char("Origin Key",
        ), 'get_origin_key')

    @property
    def sort_key(self):
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
                key.append(DualRecord(sale))

        elif self.shipment and isinstance(self.shipment, ShipmentIn):
            if self.origin and 'purchase.line' in str(self.origin):
                purchase = self.origin.purchase
                if purchase in key:
                    key.append(DualRecord(purchase))
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


class MoveDiscount(HTMLDiscountReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.move'


class ShipmentInternal(HTMLPartyInfoMixin, metaclass=PoolMeta):
    __name__ = 'stock.shipment.internal'
    show_lots = fields.Function(fields.Boolean('Show Lots'),
        'get_show_lots')

    @classmethod
    def __setup__(cls):
        super(ShipmentInternal, cls).__setup__()
        cls.html_party.context = {'company': Eval('company', -1)}
        cls.html_party.depends = ['company']

    def get_html_party(self, name):
        return

    def get_show_lots(self, name):
        for move in self.moves:
            if hasattr(move, 'lot') and getattr(move, 'lot'):
                return True
        return False


class StockInventory(HTMLReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.inventory'


class StockReportMixin(DominateReportMixin):
    @classmethod
    def show_carrier(cls, carrier):
        container = div()
        with container:
            raw(carrier.party.render.name)
            br()
            if carrier.party.raw.tax_identifier:
                raw(carrier.party.tax_identifier.render.code)
        return container

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
    def show_totals(cls, record):
        return record.company.raw.__class__.show_totals(record)

    @classmethod
    def _get_language(cls, record):
        if record:
            if getattr(record.raw, 'customer', None):
                party = record.customer
                if party and party.raw.lang:
                    return party.raw.lang.code
            if getattr(record.raw, 'supplier', None):
                party = record.supplier
                if party and party.raw.lang:
                    return party.raw.lang.code
        return super()._get_language(record)

    @classmethod
    def _header_with_document_info(cls, record, document_info_node):
        company = record.company
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
                            document_info_node
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
    def _footer(cls, record):
        company = record.company
        footer = div()
        with footer:
            link(rel='stylesheet', href=cls._base_css_href())
            with footer_tag(id='footer', align='center'):
                cls.show_footer(company)
        return footer

    @classmethod
    def _show_stock_moves(cls, document, valued=False):
        moves_table = table(style='width:100%;')
        with moves_table:
            with thead():
                with tr():
                    th(cls.label('product.product', 'code'),
                        nowrap=True)
                    th(cls.label('product.template', 'name'),
                        nowrap=True)
                    if document.raw.show_lots:
                        th(cls.label('stock.move', 'lot'))
                    th(cls.label('stock.move', 'quantity'),
                        cls='text-right', nowrap=True)
                    th(cls.label('stock.move', 'unit'),
                        nowrap=True)
                    if valued:
                        th(cls.label('stock.move', 'base_price'),
                            cls='text-right')
                        th('', cls='text-right')
                        th(cls.label('stock.move', 'amount'),
                            cls='text-right')
                    else:
                        th('', cls='hide')
                        th('', cls='hide')
                        th('', cls='hide')
            with tbody(cls='border'):
                for key in document.raw.sorted_keys:
                    if key:
                        with tr():
                            cell = th(cls='sub_header', colspan='9')
                            lines = []
                            for item in key:
                                if getattr(item.raw, 'sale_date', None):
                                    label_date = cls.label(
                                        item.raw.__name__, 'sale_date')
                                    item_date = (item.render.sale_date
                                        if getattr(item.raw, 'sale_date', None)
                                        else None)
                                else:
                                    label_date = cls.label(
                                        item.raw.__name__, 'effective_date')
                                    item_date = (item.render.effective_date
                                        if getattr(item.raw, 'effective_date',
                                            None) else None)
                                text = '%s : %s' % (
                                    cls.label(item.raw.__name__),
                                    item.render.number
                                    if getattr(item.raw, 'number', None) else '')
                                if item_date:
                                    text += ' %s : %s' % (
                                        label_date, item_date)
                                lines.append(text)
                            cell.add(raw('<br/>'.join(lines)))
                    for move in document.sorted_lines:
                        if move.raw.sort_key != key:
                            continue
                        with tr():
                            td(move.product and move.product.render.code or '-')
                            td(move.product and move.product.render.name or '-')
                            if document.raw.show_lots:
                                lot_value = ''
                                if move.lot:
                                    lot_value = move.lot.render.number
                                    if (move.raw.lot
                                            and getattr(move.lot.raw,
                                                'expiration_date', None)):
                                        lot_value += ' (%s)' % (
                                            move.lot.render.expiration_date)
                                td(lot_value)
                            td(move.render.quantity, cls='text-right')
                            td(move.unit.render.name)
                            if valued:
                                currency = (document.currency.render.symbol
                                    if document.currency else '')
                                base_price = getattr(move.raw, 'base_price',
                                    None)
                                discount = getattr(move.raw, 'discount', None)
                                amount = getattr(move.raw, 'amount', None)
                                if base_price is not None:
                                    td('%s %s' % (
                                        move.render.base_price, currency),
                                        cls='text-right', nowrap=True)
                                else:
                                    td('', cls='text-right', nowrap=True)
                                if discount:
                                    td(move.render.discount, cls='text-right',
                                        nowrap=True)
                                else:
                                    td('', cls='text-right', nowrap=True)
                                if amount is not None:
                                    td('%s %s' % (move.render.amount, currency),
                                        cls='text-right', nowrap=True)
                                else:
                                    td('', cls='text-right', nowrap=True)
                            else:
                                td('', cls='hide')
                                td('', cls='hide')
                                td('', cls='hide')
        return moves_table

    @classmethod
    def _show_picking_moves(cls, moves, show_lots):
        moves_table = table(style='width:100%;')
        with moves_table:
            with thead():
                with tr():
                    th(cls.label('product.product', 'code'),
                        nowrap=True)
                    th(cls.label('product.template', 'name'),
                        nowrap=True)
                    if show_lots:
                        th(cls.label('stock.move', 'lot'))
                    th(cls.label('stock.move', 'quantity'),
                        cls='text-right', nowrap=True)
                    th(cls.label('stock.move', 'unit'),
                        nowrap=True)
            with tbody(cls='border'):
                for move in moves:
                    with tr():
                        td(move.product and move.product.render.code or '')
                        td(move.product and move.product.render.name or '-')
                        if show_lots:
                            lot_value = ''
                            if move.lot:
                                lot_value = move.lot.render.number
                                if (move.raw.lot
                                        and getattr(move.lot.raw,
                                            'expiration_date', None)):
                                    lot_value += ' (%s)' % (
                                        move.lot.render.expiration_date)
                            td(lot_value)
                        td(move.render.quantity, cls='text-right')
                        td(move.unit.render.name)
                    tr(style='border-bottom: 1px solid black;')
        return moves_table

    @classmethod
    def _show_internal_picking_moves(cls, record, show_lots):
        moves = record.incoming_moves or record.moves
        moves_table = table(style='width:100%;')
        with moves_table:
            with thead():
                with tr():
                    th(cls.label('product.product', 'code'),
                        nowrap=True)
                    th(cls.label('product.template', 'name'),
                        nowrap=True)
                    if show_lots:
                        th(cls.label('stock.move', 'lot'))
                    th(cls.label('stock.move', 'quantity'),
                        cls='text-right', nowrap=True)
                    th(cls.label('stock.move', 'unit'),
                        nowrap=True)
            with tbody(cls='border'):
                for move in moves:
                    with tr():
                        td(move.product and move.product.render.code or '')
                        td(move.product and move.product.render.name or '-')
                        if show_lots:
                            lot_value = ''
                            if move.lot:
                                lot_value = move.lot.render.number
                                if (move.raw.lot
                                        and getattr(move.lot.raw,
                                            'expiration_date', None)):
                                    lot_value += ' (%s)' % (
                                        move.lot.render.expiration_date)
                            td(lot_value)
                        td(move.render.quantity, cls='text-right')
                        td(move.unit.render.name)
        return moves_table

    @classmethod
    def _show_customer_return_stock_moves(cls, document, valued=False):
        show_lots = document.raw.show_lots
        show_expiration = False
        if show_lots and document.incoming_moves:
            show_expiration = bool(getattr(
                document.incoming_moves[0].raw, 'expiration_date', None))
        moves_table = table(style='width:100%;')
        with moves_table:
            with thead():
                with tr():
                    th(cls.label('product.product', 'code'),
                        nowrap=True)
                    th(cls.label('product.template', 'name'),
                        nowrap=True)
                    if show_lots:
                        th(cls.label('stock.move', 'lot'))
                        if show_expiration:
                            th(cls.label('stock.lot',
                                'expiration_date'))
                        else:
                            th('', cls='hide')
                    else:
                        th('', cls='hide')
                    th(cls.label('stock.move', 'quantity'),
                        cls='text-right', nowrap=True)
                    th(cls.label('stock.move', 'unit'),
                        nowrap=True)
                    if valued:
                        th(cls.label('stock.move', 'base_price'),
                            cls='text-right')
                        th('', cls='text-right')
                        th(cls.label('stock.move', 'amount'),
                            cls='text-right')
                    else:
                        th('', cls='hide')
                        th('', cls='hide')
                        th('', cls='hide')
            with tbody(cls='border'):
                for move in document.incoming_moves:
                    with tr():
                        td(move.product and move.product.render.code or '-')
                        td(move.product and move.product.render.name or '-')
                        if show_lots:
                            if move.lot:
                                td(move.lot.render.number)
                            else:
                                td('')
                            if move.raw.lot and getattr(
                                    move.lot.raw, 'expiration_date', None):
                                td(move.lot.render.expiration_date)
                            else:
                                td('')
                        else:
                            td('')
                        td(move.render.quantity, cls='text-right')
                        td(move.unit.render.name)
                        if valued:
                            base_price = getattr(move.raw, 'base_price', None)
                            discount = getattr(move.raw, 'discount', None)
                            amount = getattr(move.raw, 'amount', None)
                            td(move.render.base_price
                                if base_price is not None else '',
                                cls='text-right', nowrap=True)
                            if discount:
                                td(move.render.discount, cls='text-right',
                                    nowrap=True)
                            else:
                                td('', cls='text-right', nowrap=True)
                            td(move.render.amount if amount is not None else '',
                                cls='text-right', nowrap=True)
                        else:
                            td('', cls='hide')
                            td('', cls='hide')
                            td('', cls='hide')
        return moves_table

    @classmethod
    def _show_return_stock_moves(cls, document, valued=False):
        show_lots = document.raw.show_lots
        show_expiration = False
        if show_lots and document.moves:
            show_expiration = bool(getattr(
                document.moves[0].raw, 'expiration_date', None))
        moves_table = table(style='width:100%;')
        with moves_table:
            with thead():
                with tr():
                    th(cls.label('product.product', 'code'),
                        nowrap=True)
                    th(cls.label('product.template', 'name'),
                        nowrap=True)
                    if show_lots:
                        th(cls.label('stock.move', 'lot'))
                        if show_expiration:
                            th(cls.label('stock.lot',
                                'expiration_date'))
                        else:
                            th('', cls='hide')
                    else:
                        th('', cls='hide')
                    th(cls.label('stock.move', 'quantity'),
                        cls='text-right', nowrap=True)
                    th(cls.label('stock.move', 'unit'),
                        nowrap=True)
                    if valued:
                        th(cls.label('stock.move', 'base_price'),
                            cls='text-right')
                        th('', cls='text-right')
                        th(cls.label('stock.move', 'amount'),
                            cls='text-right')
                    else:
                        th('', cls='hide')
                        th('', cls='hide')
                        th('', cls='hide')
            with tbody(cls='border'):
                for move in document.moves:
                    with tr():
                        td(move.product and move.product.render.code or '-')
                        td(move.product and move.product.render.name or '-')
                        if show_lots:
                            td(move.lot and move.lot.raw.number or '')
                            if move.raw.lot and getattr(
                                    move.lot.raw, 'expiration_date', None):
                                td(move.lot.render.expiration_date)
                            else:
                                td('')
                        else:
                            td('')
                        td(move.render.quantity, cls='text-right')
                        td(move.unit.render.name)
                        if valued:
                            base_price = getattr(move.raw, 'base_price', None)
                            discount = getattr(move.raw, 'discount', None)
                            amount = getattr(move.raw, 'amount', None)
                            td(move.render.base_price
                                if base_price is not None else '',
                                cls='text-right', nowrap=True)
                            if discount:
                                td(move.render.discount, cls='text-right',
                                    nowrap=True)
                            else:
                                td('', cls='text-right', nowrap=True)
                            td(move.render.amount if amount is not None else '',
                                cls='text-right', nowrap=True)
                        else:
                            td('', cls='hide')
                            td('', cls='hide')
                            td('', cls='hide')
        return moves_table

    @classmethod
    def _show_restocking_list_info(cls, record):
        title = cls.label(record.raw.__name__)
        container = div()
        with container:
            p(record.company.render.rec_name)
            h1('Restocking List', cls='title')
            h1('%s: %s' % (title,
                record.render.number if record.raw.number else ''), cls='document')
            h2('%s: %s' % (
                cls.label('stock.shipment.in', 'reference'),
                record.render.origins if record.raw.origins
                else record.render.reference or ''), cls='document')
            h2('%s: %s' % (
                cls.label('stock.shipment.in', 'supplier'),
                record.supplier.render.rec_name or ''), cls='document')
            h2('%s: %s' % (
                cls.message('stock.msg_shipment_planned_date'),
                record.render.planned_date or ''), cls='document')
            h2('%s: %s' % (
                cls.label('stock.shipment.in', 'warehouse'),
                record.warehouse.render.rec_name), cls='document')
        return container

    @classmethod
    def _show_restocking_list_moves(cls, shipment):
        moves = (shipment.incoming_moves if
            shipment.warehouse_input == shipment.warehouse_storage
            else shipment.inventory_moves)
        moves_table = table(style='width:100%;')
        with moves_table:
            with thead():
                with tr():
                    th(cls.label('stock.move', 'from_location'),
                        nowrap=True)
                    th(cls.label('stock.move', 'to_location'),
                        nowrap=True)
                    th(cls.label('stock.move', 'product'),
                        nowrap=True)
                    if shipment.raw.show_lots:
                        th(cls.label('stock.move', 'lot'),
                            nowrap=True)
                    th(cls.label('stock.move', 'quantity'),
                        nowrap=True)
            with tbody(cls='border'):
                for move in moves:
                    with tr():
                        td(move.from_location.render.rec_name)
                        td(move.to_location.render.rec_name)
                        td(move.product.render.rec_name)
                        if shipment.raw.show_lots:
                            lot_value = ''
                            if move.lot:
                                lot_value = move.lot.render.number
                                if (move.raw.lot
                                        and getattr(move.lot.raw,
                                            'expiration_date', None)):
                                    lot_value += ' (%s)' % (
                                        move.lot.render.expiration_date)
                            td(lot_value)
                        td(move.render.quantity)
        return moves_table

    @classmethod
    def _show_inventory_lines(cls, inventory):
        lines_table = table(style='width:100%;')
        with lines_table:
            with thead():
                th(cls.label('stock.inventory.line', 'product'),
                    nowrap=True)
                th(cls.label('stock.inventory.line',
                    'expected_quantity'), cls='text-right')
                th(cls.label('stock.inventory.line', 'quantity'),
                    cls='text-right')
            with tbody(cls='border'):
                for line in inventory.lines:
                    with tr():
                        td('%s - %s' % (
                            line.product and line.product.render.code,
                            line.product and line.product.render.name))
                        td(line.render.expected_quantity or 0,
                            cls='text-right')
                        td(line.render.quantity or 0, cls='text-right')
        return lines_table


class StockInventoryReport(StockReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.inventory'

    @classmethod
    def header(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        header = div()
        with header:
            link(rel='stylesheet', href=cls._base_css_href())
            with header_tag(id='header'):
                with table():
                    with tr():
                        with td():
                            strong('%s:' % cls.label(
                                'stock.inventory', 'number'))
                            raw(' %s' % record.render.number)
                        with td():
                            strong('%s:' % cls.label(
                                'stock.inventory', 'date'))
                            raw(' %s' % record.render.date)
                    with tr():
                        with td():
                            strong('%s:' % cls.label(
                                'stock.inventory', 'location'))
                            raw(' %s' % record.location.render.name)
                        td('')
        return header

    @classmethod
    def title(cls, action, record=None, records=None, data=None):
        return cls.label('stock.inventory')

    @classmethod
    def body(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        container = div()
        with container:
            container.add(cls._show_inventory_lines(record))
        return container


class DeliveryNoteReport(StockReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.shipment.out.delivery_note'

    @classmethod
    def _document_info(cls, record):
        title = cls.label(record.raw.__name__)
        document_date = (record.render.effective_date
            if getattr(record.raw, 'effective_date', None) else '')
        container = div()
        with container:
            if record.raw.state not in ['assigned', 'picked', 'packed', 'done']:
                h1('Draft', cls='document')
            h1('%s: %s' % (title,
                record.render.number if record.raw.number else ''),
                cls='document')
            h2('%s: %s' % (
                cls.message('stock.msg_shipment_effective_date'),
                document_date), cls='document')
            sale_references = getattr(record.raw, 'sale_references', None)
            if sale_references:
                h2('%s: %s' % (
                    cls.label(record.raw.__name__,
                        'sale_references'),
                    record.render.sale_references), cls='document')
        return container

    @classmethod
    def header(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        return cls._header_with_document_info(record, cls._document_info(record))

    @classmethod
    def footer(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        return cls._footer(record)

    @classmethod
    def title(cls, action, record=None, records=None, data=None):
        return cls.label('stock.shipment.out')

    @classmethod
    def body(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        container = div()
        with container:
            container.add(cls._show_stock_moves(record, valued=False))
            if getattr(record.raw, 'carrier', None):
                container.add(cls.show_carrier(record.carrier))
            if getattr(record.raw, 'comment', None):
                h4(cls.label(record.raw.__name__, 'comment'))
                p(raw(record.render.comment))
        return container


class ValuedDeliveryNoteReport(DeliveryNoteReport, metaclass=PoolMeta):
    __name__ = 'stock.shipment.out.valued_delivery_note'

    @classmethod
    def last_footer(cls, action, record=None, records=None, data=None):
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
                        td('')
                        with td():
                            cls.show_totals(record)
        return last_footer

    @classmethod
    def body(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        container = div()
        with container:
            container.add(cls._show_stock_moves(record, valued=True))
            if getattr(record.raw, 'carrier', None):
                p(cls.show_carrier(record.carrier))
            if getattr(record.raw, 'comment', None):
                h4(cls.label(record.raw.__name__, 'comment'))
                p(raw(record.render.comment))
        return container


class PickingNoteReport(StockReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.shipment.out.picking_note'

    @classmethod
    def _document_info(cls, record):
        title = cls.label(record.raw.__name__)
        document_date = (record.render.effective_date
            if getattr(record.raw, 'effective_date', None) else '')
        label_package = None
        if getattr(record.raw, 'number_packages', None):
            label_package = cls.label(
                record.raw.__name__, 'number_packages')
        container = div()
        with container:
            if record.raw.state not in ['assigned', 'picked', 'packed', 'done']:
                h1('Draft', cls='document')
            h1('%s: %s' % (title,
                record.render.number if record.raw.number else ''),
                cls='document')
            h2('%s: %s' % (
                cls.message('stock.msg_shipment_effective_date'),
                document_date), cls='document')
            if label_package:
                h3('%s: %s' % (
                    label_package, record.render.number_packages),
                    cls='document')
        return container

    @classmethod
    def header(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        return cls._header_with_document_info(record, cls._document_info(record))

    @classmethod
    def footer(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        return cls._footer(record)

    @classmethod
    def title(cls, action, record=None, records=None, data=None):
        return cls.label('stock.shipment.out')

    @classmethod
    def body(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        moves = record.inventory_moves or record.outgoing_moves
        container = div()
        with container:
            container.add(cls._show_picking_moves(moves, record.raw.show_lots))
        return container


class InternalPickingNoteReport(StockReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.shipment.internal_picking_note'

    @classmethod
    def _document_info(cls, record):
        title = cls.label(record.raw.__name__)
        document_date = (record.render.effective_date
            if getattr(record.raw, 'effective_date', None) else '')
        label_package = None
        if getattr(record.raw, 'number_packages', None):
            label_package = cls.label(
                record.raw.__name__, 'number_packages')
        container = div()
        with container:
            if record.raw.state not in ['assigned', 'picked', 'packed', 'done']:
                h1('Draft', cls='document')
            h1('%s: %s' % (title,
                record.render.number if record.raw.number else ''),
                cls='document')
            h2('%s: %s' % (
                cls.message('stock.msg_shipment_effective_date'),
                document_date), cls='document')
            if label_package:
                h3('%s: %s' % (
                    label_package, record.render.number_packages),
                    cls='document')
            h3('%s: %s' % (
                cls.label('stock.shipment.internal',
                    'from_location'),
                record.from_location.render.name), cls='document')
            h3('%s: %s' % (
                cls.label('stock.shipment.internal',
                    'to_location'),
                record.to_location.render.name), cls='document')
        return container

    @classmethod
    def header(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        return cls._header_with_document_info(record, cls._document_info(record))

    @classmethod
    def footer(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        return cls._footer(record)

    @classmethod
    def title(cls, action, record=None, records=None, data=None):
        return cls.label('stock.shipment.out')

    @classmethod
    def body(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        container = div()
        with container:
            container.add(cls._show_internal_picking_moves(
                record, record.raw.show_lots))
        return container


class CustomerRefundNoteReport(StockReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.shipment.out.refund_note'

    @classmethod
    def _document_info(cls, record):
        title = cls.label(record.raw.__name__)
        document_date = (record.render.effective_date
            if getattr(record.raw, 'effective_date', None) else '')
        container = div()
        with container:
            h1('%s: %s' % (title,
                record.render.number if record.raw.number else ''),
                cls='document')
            h2('%s: %s' % (
                cls.message('stock.msg_shipment_effective_date'),
                document_date), cls='document')
        return container

    @classmethod
    def header(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        return cls._header_with_document_info(record, cls._document_info(record))

    @classmethod
    def footer(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        return cls._footer(record)

    @classmethod
    def title(cls, action, record=None, records=None, data=None):
        return cls.label('stock.shipment.in.return')

    @classmethod
    def body(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        container = div()
        with container:
            container.add(cls._show_customer_return_stock_moves(
                record, valued=False))
            if getattr(record.raw, 'carrier', None):
                container.add(cls.show_carrier(record.carrier))
            if getattr(record.raw, 'comment', None):
                br()
                br()
                strong(cls.label(record.raw.__name__, 'comment'))
                br()
                raw(record.render.comment)
        return container


class RefundNoteReport(CustomerRefundNoteReport, metaclass=PoolMeta):
    __name__ = 'stock.shipment.in.refund_note'

    @classmethod
    def body(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        container = div()
        with container:
            container.add(cls._show_return_stock_moves(record, valued=False))
            if getattr(record.raw, 'carrier', None):
                container.add(cls.show_carrier(record.carrier))
            if getattr(record.raw, 'comment', None):
                br()
                br()
                strong(cls.label(record.raw.__name__, 'comment'))
                br()
                raw(record.render.comment)
        return container


class SupplierRestockingListReport(StockReportMixin, metaclass=PoolMeta):
    __name__ = 'stock.shipment.in.restocking_list'

    @classmethod
    def _get_language(cls, record):
        return DominateReportMixin._get_language(record)

    @classmethod
    def title(cls, action, record=None, records=None, data=None):
        return cls.label('stock.shipment.in')

    @classmethod
    def body(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        container = div()
        with container:
            container.add(cls._show_restocking_list_info(record))
            container.add(cls._show_restocking_list_moves(record))
        return container
