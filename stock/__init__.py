from trytond.pool import Pool
from . import stock

def register(module):
    Pool.register(
        stock.ShipmentOut,
        stock.ShipmentOutReturn,
        stock.ShipmentInternal,
        stock.ShipmentIn,
        stock.ShipmentInReturn,
        stock.Move,
        stock.StockInventory,
        module=module, type_='model', depends=['stock'])
    Pool.register(
        stock.MoveDiscount,
        module=module,
        type_='model',
        depends=['stock_valued'])
