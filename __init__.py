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
        module=module, type_='model', depends=['account', 'company'])
    Pool.register(
        translation.ReportTranslationSet,
        module=module, type_='wizard')
    Pool.register_mixin(engine.HTMLReportMixin, Report,
        module=module)

    product.register(module)
    invoice.register(module)
    production.register(module)
    purchase.register(module)
    sale.register(module)
    sale_product_customer.register(module)
    stock.register(module)
