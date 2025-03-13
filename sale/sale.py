from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.modules.html_report.template import HTMLPartyInfoMixin
from trytond.modules.html_report.engine import HTMLReportMixin
from trytond.modules.html_report.discount import HTMLDiscountReportMixin


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
