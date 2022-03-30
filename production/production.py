from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.modules.html_report.html import HTMLPartyInfoMixin


class Production(HTMLPartyInfoMixin, metaclass=PoolMeta):
    __name__ = 'production'
    show_lots = fields.Function(fields.Boolean('Production'),
        'get_show_lots')

    @classmethod
    def __setup__(cls):
        super(Production, cls).__setup__()
        cls.html_party.context = {'company': Eval('company')}
        cls.html_party.depends = ['company']

    def get_show_lots(self, name):
        for move in self.inputs:
            if getattr(move, 'lot'):
                return True
        return False

    def get_html_party(self, name):
        return
