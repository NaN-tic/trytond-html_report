# This file is part html_report module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from trytond.report import Report
from . import action
from . import translation
from . import template
from . import engine
from . import product
from . import invoice
from . import production
from . import purchase
from . import sale
from . import sale_product_customer
from . import stock
from . import account_configuration
from . import company

def register():
    module = 'html_report'
    Pool.register(
        action.ActionReport,
        action.HTMLTemplateTranslation,
        template.Signature,
        template.Template,
        template.TemplateUsage,
        template.ReportTemplate,
        module=module, type_='model')
    Pool.register(
        account_configuration.Configuration,
        account_configuration.ConfigurationHTMLReport,
        company.Company,
        module=module, type_='model', depends=['account', 'company'])
    Pool.register(
        translation.ReportTranslationSet,
        module=module, type_='wizard')
    Pool.register_mixin(engine.HTMLReportMixin, Report,
        module=module)

    Pool.register(
        invoice.Invoice,
        invoice.InvoiceLine,
        module=module, type_='model', depends=['account_invoice'])
    Pool.register(
        invoice.InvoiceLineDiscount,
        module=module,
        type_='model',
        depends=['account_invoice', 'account_invoice_discount'])
    Pool.register(
        invoice.InvoiceReport,
        module=module, type_='report', depends=[
            'account_invoice'])

    Pool.register(
        sale.Sale,
        module=module, type_='model', depends=['sale'])
    Pool.register(
        sale.SaleLineDiscount,
        module=module,
        type_='model',
        depends=['sale', 'sale_discount'])
    Pool.register(
        sale.SaleReport,
        module=module, type_='report', depends=['sale'])

    Pool.register(
        purchase.Purchase,
        module=module, type_='model', depends=['purchase'])
    Pool.register(
        purchase.PurchaseLineDiscount,
        module=module,
        type_='model',
        depends=['purchase', 'purchase_discount'])
    Pool.register(
        purchase.PurchaseReport,
        purchase.PurchaseSimplifiedReport,
        module=module, type_='report', depends=['purchase'])

    Pool.register(
        production.Production,
        module=module, type_='model', depends=['production'])
    Pool.register(
        production.ProductionReport,
        module=module, type_='report', depends=['production'])

    Pool.register(
        stock.ShipmentOut,
        stock.ShipmentOutReturn,
        stock.ShipmentInternal,
        stock.ShipmentIn,
        stock.ShipmentInReturn,
        stock.Move,
        stock.StockInventory,
        module=module, type_='model', depends=['stock'])
    Pool.register(
        stock.MoveDiscount,
        module=module,
        type_='model',
        depends=['stock_valued'])
    Pool.register(
        stock.StockInventoryReport,
        stock.DeliveryNoteReport,
        stock.ValuedDeliveryNoteReport,
        stock.PickingNoteReport,
        stock.InternalPickingNoteReport,
        stock.CustomerRefundNoteReport,
        stock.RefundNoteReport,
        stock.SupplierRestockingListReport,
        module=module, type_='report', depends=['stock'])
    product.register(module)
    sale_product_customer.register(module)
