from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.modules.html_report.template import HTMLPartyInfoMixin


class Purchase(HTMLPartyInfoMixin, metaclass=PoolMeta):
    __name__ = 'purchase.purchase'

    @classmethod
    def __setup__(cls):
        super(Purchase, cls).__setup__()
        cls.html_party.context = {'company': Eval('company')}
        cls.html_party.depends = ['company']

    def get_html_address(self, name):
        return (self.invoice_address and self.invoice_address.id
            or super().get_html_address(name))
