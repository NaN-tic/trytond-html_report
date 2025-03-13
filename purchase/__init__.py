from trytond.pool import Pool
from . import purchase


def register(module):
    Pool.register(
        purchase.Purchase,
        module=module, type_='model', depends=['purchase'])
    Pool.register(
        purchase.PurchaseLineDiscount,
        module=module,
        type_='model',
        depends=['purchase', 'purchase_discount'])
