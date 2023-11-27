from trytond.pool import Pool
from . import product

def register(module):
    Pool.register(
        product.Product,
        module=module, type_='model', depends=['product'])
