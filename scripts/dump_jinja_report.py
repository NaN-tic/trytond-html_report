from datetime import datetime
from trytond.transaction import Transaction

pool = globals()['pool']
Report = pool.get('ir.action.report')

with Transaction().set_context(active_test=False):
    reports = Report.search([
        ('template_extension', '=', 'jinja'),
        ])

output_path = '/tmp/%s_html_report_jinja.txt' % Transaction().database.name

with open(output_path, 'w', encoding='utf-8') as f:
    f.write('dumped_at: %s\n' % datetime.utcnow().isoformat())
    f.write('database: %s\n' % Transaction().database.name)
    f.write('report_filter: template_extension=jinja\n\n')
    for report in reports:
        f.write('report_id: %s\n' % report.id)
        f.write('name: %s\n' % report.name)
        f.write('model: %s\n' % report.model)
        f.write('template_extension: %s\n\n' % report.template_extension)

        def template_content(template):
            if not template:
                return ''
            return template.all_content or template.content or ''

        f.write('--- html_header_template ---\n')
        f.write(template_content(report.html_header_template))
        f.write('\n\n--- html_template ---\n')
        f.write(template_content(report.html_template))
        f.write('\n\n--- html_footer_template ---\n')
        f.write(template_content(report.html_footer_template))
        f.write('\n\n--- html_last_footer_template ---\n')
        f.write(template_content(report.html_last_footer_template))
        f.write('\n\n--- html_content ---\n')
        f.write(report.html_content or '')
        f.write('\n\n')

print('Wrote %s' % output_path)
