from trytond.pool import PoolMeta
from trytond.model import fields


class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    html_code = fields.Function(fields.Char(
        "HTML Code"), 'get_html_code')

    def get_html_code(self, name):
        return self.code or ''
