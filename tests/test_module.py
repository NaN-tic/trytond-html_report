# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from decimal import Decimal
from trytond.tests.test_tryton import (ModuleTestCase, with_transaction,
    activate_module)
from trytond.pool import Pool
from trytond.tools import file_open
from trytond.transaction import Transaction
from trytond.modules.company.tests import CompanyTestMixin, create_company, set_company
from trytond.modules.account.tests import create_chart, get_fiscalyear
from trytond.modules.account_invoice.tests import set_invoice_sequences


class HtmlReportTestCase(CompanyTestMixin, ModuleTestCase):
    'Test HtmlReport module'
    module = 'html_report'

    @classmethod
    def setUpClass(cls):
        super(HtmlReportTestCase, cls).setUpClass()
        activate_module('account_invoice')
        activate_module('account_payment_type')
        activate_module('account_invoice_discount')
        activate_module('account_bank')
        activate_module('carrier')
        activate_module('sale')
        activate_module('sale_product_customer')
        activate_module('purchase')
        activate_module('stock')
        activate_module('stock_valued')
        activate_module('production')

    @with_transaction()
    def test_html_report(self):
        'Create HTML Report'
        pool = Pool()
        ActionReport = pool.get('ir.action.report')
        Template = pool.get('html.template')
        HTMLTemplateTranslation = pool.get('html.template.translation')
        Model = pool.get('ir.model')

        model, = Model.search([('model', '=', 'ir.model')], limit=1)

        with file_open('html_report/tests/base.html') as f:
            tpl_base, = Template.create([{
                        'name': 'Base',
                        'type': 'base',
                        'content': f.read(),
                        }])

        with file_open('html_report/tests/models.html') as f:
            tpl_models, = Template.create([{
                        'name': 'Modules',
                        'type': 'extension',
                        'content': f.read(),
                        'parent': tpl_base,
                        }])

        report, = ActionReport.create([{
            'name': 'Models',
            'model': 'ir.model',
            'report_name': 'ir.model.report',
            'template_extension': 'jinja',
            'extension': 'html',
            'html_template': tpl_models,
            }])

        models = Model.search([('model', 'like', 'ir.model%')])

        self.assertTrue(report.id)
        self.assertTrue('block body' in report.html_content, True)

        HTMLTemplateTranslation.create([{
                'lang': 'es',
                'src': 'Name',
                'value': 'Nombre',
                'report': report.id,
                }, {
                'lang': 'es',
                'src': 'Model',
                'value': 'Modelo',
                'report': report.id,
                }])

        with Transaction().set_context(language='es'):
            ModelReport = Pool().get('ir.model.report', type='report')
            ext, content, _, filename = ModelReport.execute([m.id for m in models], {})
            self.assertTrue(ext, 'html')
            self.assertTrue('ir.model' in content, True)
            self.assertTrue('Nombre' in content, True)
            self.assertTrue('Modelo' in content, True)
            # has not translation because test not load locale/es.po translations (-l es)
            self.assertTrue('Created by' in content, True)
            self.assertTrue(filename.startswith('Models'))

            report.html_file_name = '{{ record.render.rec_name }} {{ record.render.id }}'
            report.save()
            ext, content, _, filename = ModelReport.execute([m.id for m in models], {})
            self.assertTrue(filename.startswith('Model-'))

        report2, = ActionReport.copy([report], {'report_name': 'ir.model.report2', 'extension': None})
        ModelReport2 = Pool().get('ir.model.report2', type='report')
        ext, content, _, _ = ModelReport2.execute([m.id for m in models], {})
        self.assertTrue(isinstance(content, bytes))

        with Transaction().set_context(output_format='html'):
            ext, content, _, _ = ModelReport2.execute([m.id for m in models], {})
            self.assertTrue(isinstance(content, str))
            self.assertTrue(content.startswith('<!DOCTYPE html>'))

    @with_transaction()
    def test_check_reports(self):
        pool = Pool()
        Report = pool.get('ir.action.report')
        FiscalYear = pool.get('account.fiscalyear')
        Account = pool.get('account.account')
        Party = pool.get('party.party')
        PaymentTerm = pool.get('account.invoice.payment_term')
        Uom = pool.get('product.uom')
        Template = pool.get('product.template')
        Category = pool.get('product.category')
        Uom = pool.get('product.uom')
        Sale = pool.get('sale.sale')
        Purchase = pool.get('purchase.purchase')
        Location = pool.get('stock.location')
        ShipmentInternal = pool.get('stock.shipment.internal')

        company = create_company()
        with set_company(company):
            create_chart(company)

            fiscalyear = get_fiscalyear(company)
            set_invoice_sequences(fiscalyear)
            fiscalyear.save()
            FiscalYear.create_period([fiscalyear])

            account_revenue, = Account.search([
                        ('type.revenue', '=', True),
                        ('company', '=', company.id),
                        ])
            account_expense, = Account.search([
                        ('type.expense', '=', True),
                        ('company', '=', company.id),
                        ])

            payment_term, = PaymentTerm.create([{
                        'name': 'Test',
                        'lines': [
                            ('create', [{
                                        'type': 'remainder',
                                        }])
                            ],
                        }])

            unit, = Uom.search([('name', '=', 'Unit')])

            party, = Party.create([{
                        'name': 'Party',
                        'addresses': [
                            ('create', [{}]),
                            ],
                        }])

            # category
            account_category = Category()
            account_category.name = 'Account Category'
            account_category.accounting = True
            account_category.account_expense = account_expense
            account_category.account_revenue = account_revenue
            account_category.save()

            # product
            unit, = Uom.search([('name', '=', 'Unit')])
            template1 = Template()
            for key, value in Template.default_get(Template._fields.keys(),
                    with_rec_name=False).items():
                if value is not None:
                    setattr(template1, key, value)
            template1.name = 'Product 1'
            template1.list_price = Decimal(12)
            template1.cost_price = Decimal(10)
            template1.default_uom = unit
            template1.salable = True
            template1.purchasable = True
            template1.on_change_default_uom()
            template1.account_category = account_category
            template1.save()
            product1, = template1.products

            sales = Sale.create([{
                        'party': party.id,
                        'company': company.id,
                        'payment_term': payment_term.id,
                        'currency': company.currency.id,
                        'invoice_address': party.addresses[0].id,
                        'shipment_address': party.addresses[0].id,
                        'invoice_method': 'order',
                        'shipment_method': 'order',
                        'lines': [
                            ('create', [{
                                        'product': product1,
                                        'quantity': 2,
                                        'unit_price': Decimal('25'),
                                        'unit': unit,
                                        }]),
                            ],
                        }, {
                        'party': party.id,
                        'company': company.id,
                        'payment_term': payment_term.id,
                        'currency': company.currency.id,
                        'invoice_address': party.addresses[0].id,
                        'shipment_address': party.addresses[0].id,
                        'invoice_method': 'order',
                        'shipment_method': 'order',
                        'lines': [
                            ('create', [{
                                        'product': product1,
                                        'quantity': 2,
                                        'unit_price': Decimal('25'),
                                        'unit': unit,
                                        }]),
                            ],
                        }])
            Sale.quote(sales)
            Sale.confirm(sales)
            Sale.process(sales)

            purchases = Purchase.create([{
                        'party': party.id,
                        'company': company.id,
                        'currency': company.currency.id,
                        'invoice_address': party.addresses[0].id,
                        'invoice_method': 'order',
                        'lines': [
                            ('create', [{
                                        'product': product1,
                                        'quantity': 2,
                                        'unit_price': Decimal('25'),
                                        'unit': unit,
                                        }]),
                            ],
                        }, {
                        'party': party.id,
                        'company': company.id,
                        'currency': company.currency.id,
                        'invoice_address': party.addresses[0].id,
                        'invoice_method': 'order',
                        'lines': [
                            ('create', [{
                                        'product': product1,
                                        'quantity': 2,
                                        'unit_price': Decimal('25'),
                                        'unit': unit,
                                        }]),
                            ],
                        }])
            Purchase.quote(purchases)
            Purchase.confirm(purchases)
            Purchase.process(purchases)

            storage_loc, = Location.search([('name', '=', 'Storage Zone')])
            lost_found_loc, = Location.search([('name', '=', 'Lost and Found')])

            # TODO stock.shipment.in
            shipment_internals = ShipmentInternal.create([{
                        'from_location': storage_loc.id,
                        'to_location': lost_found_loc.id,
                        'moves': [
                            ('create', [{
                                        'product': product1,
                                        'quantity': 2,
                                        'unit': unit,
                                        'from_location': storage_loc.id,
                                        'to_location': lost_found_loc.id,
                                        }]),
                            ],
                        }])
            ShipmentInternal.wait(shipment_internals)

            # TODO production

            reports = Report.search([
                    ('model', '!=', None),
                    ('template_extension', '=', 'jinja'),
                    ])

            for report in reports:
                if not report.keywords or not report.model:
                    continue

                Model = pool.get(report.model)
                records = Model.search([], limit=5, order=[('id', 'DESC')])
                # records += Model.search([], limit=5, order=[('id', 'ASC')])
                for record in records:
                    Report = pool.get(report.report_name, type='report')
                    Report.execute([record.id], data={})


del ModuleTestCase
