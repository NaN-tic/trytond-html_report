from dominate.util import raw
from dominate.tags import b, br, div, strong

from trytond.pool import PoolMeta

from .engine import DualRecord, HTMLReportMixin


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    def show_party_info(self, tax_identifier, address, second_address_label,
            second_address):
        if not self:
            return raw('')
        record = DualRecord(self)
        container = div()
        with container:
            b(record.render.name)
            br()
            if tax_identifier:
                raw(tax_identifier.render.code)
                br()
            if address:
                raw(address.render.full_address.replace('\n', '<br/>'))
            br()
            if record.raw.phone:
                raw('%s: %s' % (
                    HTMLReportMixin.label('party.party', 'phone'),
                    record.render.phone))
                br()
            if record.raw.email:
                raw(record.render.email)
                br()
            if second_address and address and second_address.raw.id != address.raw.id:
                if second_address_label:
                    strong(' %s' % second_address_label)
                    br()
                raw(second_address.render.full_address.replace('\n', '<br/>'))
        return container
