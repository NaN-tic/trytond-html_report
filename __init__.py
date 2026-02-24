# This file is part html_report module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from trytond.report import Report
from . import action
from . import translation
from . import template
from . import engine
from . import i18n
from . import invoice
from . import dominate_report
from . import production
from . import purchase
from . import sale
from . import product
from . import stock
from . import account_configuration

def register():
    module = 'html_report'
    Pool.register(
        dominate_report.DominateCommon,
        action.ActionReport,
        action.HTMLTemplateTranslation,
        template.Signature,
        template.Template,
        template.TemplateUsage,
        template.ReportTemplate,
        i18n.Translation,
        module=module, type_='model')
    Pool.register(
        dominate_report.DominateCommonCompany,
        module=module, type_='model', depends=['company'])
    Pool.register(
        dominate_report.DominateCommonParty,
        module=module, type_='model', depends=['party'])
    Pool.register(
        account_configuration.Configuration,
        account_configuration.ConfigurationHTMLReport,
        module=module, type_='model', depends=['account'])
    Pool.register(
        translation.ReportTranslationSet,
        i18n.TranslationSet,
        i18n.TranslationClean,
        i18n.TranslationUpdate,
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
    Pool.register(
        product.Product,
        module=module, type_='model', depends=['product'])
    Pool.register(
        product.ProductCustomer,
        module=module, type_='model', depends=['sale_product_customer'])
