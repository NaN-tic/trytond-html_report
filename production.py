from dominate.util import raw
from dominate.tags import (div, footer as footer_tag, h1, h2, header as header_tag,
    img, link, table, tbody, td, th, thead, tr)

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.modules.html_report.template import HTMLPartyInfoMixin
from trytond.modules.html_report.dominate_report import DominateReportMixin


class Production(HTMLPartyInfoMixin, metaclass=PoolMeta):
    __name__ = 'production'
    show_lots = fields.Function(fields.Boolean('Production'),
        'get_show_lots')

    @classmethod
    def __setup__(cls):
        super(Production, cls).__setup__()
        cls.html_party.context = {'company': Eval('company', -1)}
        cls.html_party.depends = ['company']

    def get_show_lots(self, name):
        for move in self.inputs:
            if hasattr(move, 'lot') and getattr(move, 'lot'):
                return True
        return False

    def get_html_party(self, name):
        return


class ProductionReport(DominateReportMixin, metaclass=PoolMeta):
    __name__ = 'production.production'

    @classmethod
    def show_company_info(cls, company, show_party=True,
            show_contact_mechanism=True):
        return company.raw.__class__.show_company_info(
            company, show_party=show_party,
            show_contact_mechanism=show_contact_mechanism)

    @classmethod
    def show_footer(cls, company=None):
        if company is None:
            return raw('')
        return company.raw.__class__.show_footer(company)

    @classmethod
    def _document_info(cls, record):
        title = cls.label(record.raw.__name__)
        document_date = (record.render.effective_date
            if getattr(record.raw, 'effective_date', None) else '')
        label_reference = cls.label(record.raw.__name__, 'reference')
        container = div()
        with container:
            h1('%s: %s' % (title,
                record.render.number if record.raw.number else ''),
                cls='document')
            h2('%s: %s' % (label_reference,
                record.raw.reference or ''), cls='document')
            h2('%s: %s' % (
                cls.message('stock.msg_shipment_effective_date'),
                document_date or ''), cls='document')
        return container

    @classmethod
    def _show_output_moves(cls, production):
        moves_table = table(style='width:100%;')
        show_lots = production.raw.show_lots
        show_expiration = False
        if show_lots and production.outputs:
            show_expiration = bool(getattr(
                production.outputs[0].raw, 'expiration_date', None))
        with moves_table:
            with thead():
                with tr():
                    th(cls.label('stock.move', 'from_location'),
                        nowrap=True)
                    th(cls.label('stock.move', 'to_location'),
                        nowrap=True)
                    th(cls.label('product.product', 'code'),
                        nowrap=True)
                    th(cls.label('product.template', 'name'),
                        nowrap=True)
                    if show_lots:
                        th(cls.label('stock.move', 'lot'))
                        if show_expiration:
                            th(cls.label('stock.lot',
                                'expiration_date'))
                        else:
                            th('', cls='hide')
                    else:
                        th('', cls='hide')
                    th(cls.label('stock.move', 'quantity'),
                        cls='text-right', nowrap=True)
                    th(cls.label('stock.move', 'unit'),
                        nowrap=True)
            with tbody(cls='border'):
                for move in production.outputs:
                    with tr():
                        td('%s %s' % (
                            move.from_location.render.code,
                            move.from_location.render.name))
                        td('%s %s' % (
                            move.to_location.render.code,
                            move.to_location.render.name))
                        td(move.product and move.product.render.code or '-')
                        td(move.product and move.product.render.name or '-')
                        if show_lots:
                            td(move.lot and move.lot.raw.name or '')
                            if move.raw.lot and getattr(
                                    move.lot.raw, 'expiration_date', None):
                                td(move.lot.render.expiration_date)
                            else:
                                td('')
                        else:
                            td('')
                        td(move.render.quantity, cls='text-right')
                        td(move.unit.render.name)
        return moves_table

    @classmethod
    def _show_input_moves(cls, production):
        moves_table = table(style='width:100%;')
        show_lots = production.raw.show_lots
        show_expiration = False
        if show_lots and production.inputs:
            show_expiration = bool(getattr(
                production.inputs[0].raw, 'expiration_date', None))
        with moves_table:
            with thead():
                with tr():
                    th(cls.label('stock.move', 'from_location'),
                        nowrap=True)
                    th(cls.label('stock.move', 'to_location'),
                        nowrap=True)
                    th(cls.label('product.product', 'code'),
                        nowrap=True)
                    th(cls.label('product.template', 'name'),
                        nowrap=True)
                    if show_lots:
                        th(cls.label('stock.move', 'lot'))
                        if show_expiration:
                            th(cls.label('stock.lot',
                                'expiration_date'))
                        else:
                            th('', cls='hide')
                    else:
                        th('', cls='hide')
                    th(cls.label('stock.move', 'quantity'),
                        cls='text-right', nowrap=True)
                    th(cls.label('stock.move', 'unit'),
                        nowrap=True)
            with tbody(cls='border'):
                for move in production.inputs:
                    with tr():
                        td('%s %s' % (
                            move.from_location.render.code,
                            move.from_location.render.name))
                        td('%s %s' % (
                            move.to_location.render.code,
                            move.to_location.render.name))
                        td(move.product and move.product.render.code or '-')
                        td(move.product and move.product.render.name or '-')
                        if show_lots:
                            td(move.lot and move.lot.raw.name or '')
                            if move.raw.lot and getattr(
                                    move.lot.raw, 'expiration_date', None):
                                td(move.lot.render.expiration_date)
                            else:
                                td('')
                        else:
                            td('')
                        td(move.render.quantity, cls='text-right')
                        td(move.unit.render.name)
        return moves_table

    @classmethod
    def _show_operations(cls, operations):
        ops_table = table(style='width:100%;')
        with ops_table:
            with thead():
                with tr():
                    th(cls.label('production.operation',
                        'operation_type'), nowrap=True)
                    th(cls.label('production.operation',
                        'work_center'), nowrap=True)
                    th(cls.label('production.operation',
                        'work_center_category'), nowrap=True)
                    th(cls.label('production.route.operation',
                        'time'), nowrap=True)
                    th(cls.label('production', 'quantity'),
                        nowrap=True)
            with tbody(cls='border'):
                for operation in operations:
                    with tr():
                        td(operation.operation_type.render.name or '')
                        td(operation.work_center.render.name
                            if operation.raw.work_center else '')
                        td(operation.work_center_category.render.name or '')
                        td('')
                        td('')
        return ops_table

    @classmethod
    def header(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        company = record.company
        header = div()
        with header:
            link(rel='stylesheet', href=cls._base_css_href())
            with header_tag(id='header'):
                with table():
                    with tr():
                        with td():
                            if company.render.logo:
                                img(cls='logo', src=company.render.logo)
                        with td():
                            cls._document_info(record)
                    with tr():
                        with td(cls='party_info'):
                            cls.show_company_info(company)
                        with td(cls='party_info'):
                            pass
        return header

    @classmethod
    def footer(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        company = record.company
        footer = div()
        with footer:
            link(rel='stylesheet', href=cls._base_css_href())
            with footer_tag(id='footer', align='center'):
                cls.show_footer(company)
        return footer

    def body(cls, action, record=None, records=None, data=None):
        if record is None and records:
            record = records[0]
        container = div()
        with container:
            if record.raw.product:
                product_container = div(cls='center')
                with product_container:
                    h1('%s : %s' % (
                        cls.label('production', 'product'),
                        record.product.render.rec_name))
                    h2('%s : %s %s' % (
                        cls.label('production', 'quantity'),
                        record.render.quantity,
                        record.unit.render.name))
                    if getattr(record.raw, 'route', None):
                        h2('%s : %s' % (
                            cls.label('production', 'route'),
                            record.route.render.name))
                container.add(product_container)
            h2(cls.label('production', 'outputs'))
            container.add(cls._show_output_moves(record))
            h2(cls.label('production', 'inputs'))
            container.add(cls._show_input_moves(record))
            if getattr(record.raw, 'route', None):
                container.add(cls._show_operations(record.operations))

        return container
