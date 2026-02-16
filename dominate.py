from __future__ import annotations

import zipfile
from io import BytesIO

from dominate.util import raw

from trytond.pool import Pool
from trytond.tools import slugify
from trytond.transaction import Transaction

from .engine import HTMLReportMixin
from .generator import PdfGenerator


class DominateJinjaRenderer:
    @classmethod
    def get_action_report(cls, report_name):
        if not report_name:
            return None
        ActionReport = Pool().get('ir.action.report')
        reports = ActionReport.search([('report_name', '=', report_name)],
            limit=1)
        return reports[0] if reports else None

    @classmethod
    def render_template(cls, action, template_string, **context):
        if not template_string:
            return raw('')
        html = HTMLReportMixin.render_template_jinja(
            action,
            template_string,
            record=context.get('record'),
            records=context.get('records'),
            data=context.get('data'),
        )
        return raw(html)

    @classmethod
    def render_template_html(cls, action, template_string, **context):
        node = cls.render_template(action, template_string, **context)
        return node.render()

    @classmethod
    def _get_template_for_signature(cls, action, signature_name):
        Signature = Pool().get('html.template.signature')
        Template = Pool().get('html.template')

        signatures = Signature.search([('name', '=', signature_name)],
            limit=1)
        if not signatures:
            return None
        signature = signatures[0]

        if action:
            for report_template in action.html_templates:
                if report_template.signature == signature:
                    if report_template.template_used:
                        return report_template.template_used

        templates = Template.search([('implements', '=', signature)], limit=1)
        return templates[0] if templates else None

    @classmethod
    def render_macro(cls, action, signature_name, **context):
        template = cls._get_template_for_signature(action, signature_name)
        if not template:
            return raw('')
        macro_name, args = signature_name.split('(', 1)
        args = args.rstrip(')')
        call_args = ', '.join([a.strip() for a in args.split(',') if a.strip()])
        template_string = (
            "{%% from '%s' import %s %%}{{ %s(%s) }}" % (
                template.id,
                macro_name,
                macro_name,
                call_args,
            )
        )
        return cls.render_template(action, template_string, **context)


class DominateJinjaReportMixin(HTMLReportMixin):
    """Render legacy Jinja templates into Dominate nodes and keep PDF logic."""

    @classmethod
    def render_dominate_template(cls, action, template_string, record=None,
            records=None, data=None):
        return DominateJinjaRenderer.render_template(
            action,
            template_string,
            record=record,
            records=records,
            data=data,
        )

    @classmethod
    def render_dominate_template_html(cls, action, template_string, record=None,
            records=None, data=None):
        node = cls.render_dominate_template(
            action,
            template_string,
            record=record,
            records=records,
            data=data,
        )
        return node.render()

    @classmethod
    def _execute_dominate_html_report(cls, records, data, action, side_margin=2,
            extra_vertical_margin=30):
        header_template, main_template, footer_template, last_footer_template = (
            cls.get_templates_jinja(action)
        )
        extension = data.get('output_format', action.extension or 'pdf')
        if action.single:
            documents = []
            for record in records:
                content = cls.render_dominate_template_html(
                    action, main_template, record=record, records=[record],
                    data=data)
                header = header_template and cls.render_dominate_template_html(
                    action, header_template, record=record, records=[record],
                    data=data)
                footer = footer_template and cls.render_dominate_template_html(
                    action, footer_template, record=record, records=[record],
                    data=data)
                last_footer = last_footer_template and (
                    cls.render_dominate_template_html(
                        action, last_footer_template, record=record,
                        records=[record], data=data)
                )
                if extension == 'pdf':
                    documents.append(PdfGenerator(
                        content,
                        header_html=header,
                        footer_html=footer,
                        last_footer_html=last_footer,
                        side_margin=side_margin,
                        extra_vertical_margin=extra_vertical_margin,
                    ).render_html())
                else:
                    documents.append(content)
            if extension == 'pdf' and documents:
                document = documents[0].copy([page for doc in documents
                    for page in doc.pages])
                document = document.write_pdf()
            else:
                document = ''.join(documents)
        else:
            content = cls.render_dominate_template_html(
                action, main_template, records=records, data=data)
            header = header_template and cls.render_dominate_template_html(
                action, header_template, records=records, data=data)
            footer = footer_template and cls.render_dominate_template_html(
                action, footer_template, records=records, data=data)
            last_footer = last_footer_template and (
                cls.render_dominate_template_html(
                    action, last_footer_template, records=records, data=data)
            )
            if extension == 'pdf':
                document = PdfGenerator(
                    content,
                    header_html=header,
                    footer_html=footer,
                    last_footer_html=last_footer,
                    side_margin=side_margin,
                    extra_vertical_margin=extra_vertical_margin,
                ).render_pdf()
            else:
                document = content

        if extension == 'xlsx':
            from bs4 import BeautifulSoup
            from openpyxl import Workbook
            from .tools import save_virtual_workbook, _convert_str_to_float

            wb = Workbook()
            ws = wb.active

            soup = BeautifulSoup(document, 'html.parser')
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    row_data = []
                    for cell in row.find_all(['td', 'th']):
                        row_data.append(_convert_str_to_float(cell.text))
                    ws.append(row_data)
                document = save_virtual_workbook(wb)
        return extension, document

    @classmethod
    def execute(cls, ids, data):
        action, model = cls.get_action(data)
        cls.check_access(action, model, ids)
        if action.template_extension != 'jinja':
            return super().execute(ids, data)
        action_name = cls.get_name(action)
        side_margin = action.html_side_margin
        if side_margin is None:
            side_margin = cls.side_margin
        extra_vertical_margin = action.html_extra_vertical_margin
        if extra_vertical_margin is None:
            extra_vertical_margin = cls.extra_vertical_margin

        if Transaction().context.get('output_format') == 'html':
            is_zip, is_merge_pdf, Printer = None, None, None
            output_format = data['output_format'] = 'html'
        else:
            is_zip = action.single and len(ids) > 1 and action.html_zipped
            is_merge_pdf = action.html_copies and action.html_copies > 1
            Printer = None
            try:
                Printer = Pool().get('printer')
            except KeyError:
                pass
            output_format = data.get('output_format', action.extension or 'pdf')

        data['html_dual_record'] = True
        records = []
        with Transaction().set_context(
                html_report=action.id,
                address_with_party=False,
                output_format=output_format):
            if model and ids:
                records = cls._get_dual_records(ids, model, data)

                if action.html_file_name:
                    import jinja2

                    template = jinja2.Template(action.html_file_name)
                    filename = slugify('-'.join(template.render(record=record)
                        for record in records[:5]))
                else:
                    suffix = '-'.join(r.render.rec_name for r in records[:5])
                    if len(records) > 5:
                        suffix += '__' + str(len(records[5:]))
                    filename = slugify('%s-%s' % (action_name, suffix))
            else:
                records = []
                filename = slugify(action_name)

            if is_zip:
                content = BytesIO()
                with zipfile.ZipFile(content, 'w') as content_zip:
                    for record in records:
                        oext, rcontent = cls._execute_dominate_html_report(
                            [record],
                            data,
                            action,
                            side_margin=side_margin,
                            extra_vertical_margin=extra_vertical_margin)
                        rfilename = '%s.%s' % (
                            slugify(record.render.rec_name),
                            oext)
                        if action.html_copies and action.html_copies > 1:
                            rcontent = cls.merge_pdfs(
                                [rcontent] * action.html_copies)
                        content_zip.writestr(rfilename, rcontent)
                content = content.getvalue()
                return ('zip', content, False, filename)

            oext, content = cls._execute_dominate_html_report(
                records,
                data,
                action,
                side_margin=side_margin,
                extra_vertical_margin=extra_vertical_margin)
            if content is None:
                content = ''
            if not isinstance(content, str):
                content = bytes(content)

            if is_merge_pdf:
                content = cls.merge_pdfs([content] * action.html_copies)
            if Printer:
                return Printer.send_report(oext, content,
                    action_name, action)
            return oext, content, cls.get_direct_print(action), filename
