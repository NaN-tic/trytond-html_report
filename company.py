from dominate.util import raw
from dominate.tags import br, div, span, strong, table, td, th, tr

from trytond.pool import PoolMeta

from .engine import HTMLReportMixin


class Company(metaclass=PoolMeta):
    __name__ = 'company.company'

    @classmethod
    def show_footer(cls, company=None):
        return raw('<p align="center"> </p>')

    @classmethod
    def show_company_info(cls, company, show_party=True,
            show_contact_mechanism=True):
        party = company.party
        address = party.addresses and party.addresses[0] or None
        tax_identifier = party.tax_identifier

        container = div(id='company-info', cls='header-details')
        if show_party:
            with container:
                span(company.party.render.name, cls='company-info-name')
                br()
        if tax_identifier:
            with container:
                raw(tax_identifier.render.code)
                br()
        if address:
            with container:
                with div(cls='company-info-address'):
                    raw(address.render.full_address.replace('\n', '<br/>'))
        if show_contact_mechanism:
            with container:
                with div(cls='company-info-contact-mechanims'):
                    if party.raw.phone:
                        raw('%s: %s' % (
                            HTMLReportMixin.label('party.party', 'phone'),
                            party.render.phone))
                        br()
                    if party.raw.email:
                        raw(party.render.email)
                        br()
                    if party.raw.website:
                        raw(party.render.website)
        return container

    @classmethod
    def show_payment_info(cls, document):
        container = div()
        with container:
            if getattr(document.raw, 'payment_term', None):
                strong('%s: ' % HTMLReportMixin.label(
                    document.raw.__name__, 'payment_term'))
                raw(document.payment_term.render.name)
                br()
            if getattr(document.raw, 'payment_type', None):
                strong('%s: ' % HTMLReportMixin.label(
                    document.raw.__name__, 'payment_type'))
                raw(document.payment_type.render.name)
                br()
            if getattr(document.raw, 'bank_account', None):
                strong('%s: ' % HTMLReportMixin.label(
                    document.raw.__name__, 'bank_account'))
                raw(document.bank_account.render.rec_name)
                if (document.bank_account.bank
                        and document.bank_account.bank.raw.bic):
                    raw(' (%s)' % document.bank_account.bank.render.bic)
                br()
            strong('%s:' % HTMLReportMixin.label(
                document.raw.__name__, 'currency'))
            raw(' %s' % document.currency.render.name)
            if getattr(document.raw, 'different_currencies', None):
                strong('%s:' % HTMLReportMixin.label(
                    document.raw.__name__, 'currency'))
                raw(' %s' % document.company.currency.render.name)
                strong('%s:' % HTMLReportMixin.label(
                    document.raw.__name__, 'company_untaxed_amount'))
                raw(' %s' % document.render.company_untaxed_amount)
                strong('%s:' % HTMLReportMixin.label(
                    document.raw.__name__, 'company_tax_amount'))
                raw(' %s' % document.render.company_tax_amount)
                strong('%s:' % HTMLReportMixin.label(
                    document.raw.__name__, 'company_total_amount'))
                raw(' %s' % document.render.company_total_amount)
        return container

    @classmethod
    def show_totals(cls, record):
        totals_table = table(id='totals')
        with totals_table:
            with tr():
                th('%s:' % HTMLReportMixin.label(record.raw.__name__,
                    'untaxed_amount'), scope='row',
                    cls='text-right total-label total-luntaxed')
                td('%s %s' % (record.render.untaxed_amount,
                    record.currency.render.symbol),
                    cls='text-right total-value total-vuntaxed')
            with tr():
                th('%s:' % HTMLReportMixin.label(record.raw.__name__,
                    'tax_amount'), scope='row',
                    cls='text-right total-label total-ltax')
                td('%s %s' % (record.render.tax_amount,
                    record.currency.render.symbol),
                    cls='text-right total-value total-vtax')
            with tr():
                th('%s:' % HTMLReportMixin.label(record.raw.__name__,
                    'total_amount'), scope='row',
                    cls='text-right total-label total-lamount')
                td('%s %s' % (record.render.total_amount,
                    record.currency.render.symbol),
                    cls='text-right total-value total-vamount')
        return totals_table
