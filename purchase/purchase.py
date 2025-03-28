from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.modules.html_report.template import HTMLPartyInfoMixin
from trytond.modules.html_report.discount import HTMLDiscountReportMixin


class Purchase(HTMLPartyInfoMixin, metaclass=PoolMeta):
    __name__ = 'purchase.purchase'

    @classmethod
    def __setup__(cls):
        super(Purchase, cls).__setup__()
        cls.html_party.context = {'company': Eval('company', -1)}
        cls.html_party.depends = ['company']

    def get_html_address(self, name):
        return (self.invoice_address and self.invoice_address.id
            or super().get_html_address(name))


class PurchaseLineDiscount(HTMLDiscountReportMixin, metaclass=PoolMeta):
    __name__ = 'purchase.line'
