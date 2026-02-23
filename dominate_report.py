from io import BytesIO
import zipfile

from dominate import document
from dominate.util import raw
from dominate.tags import meta, style

from trytond.pool import Pool
from trytond.tools import file_open, slugify
from trytond.transaction import Transaction

from .engine import HTMLReportMixin
from .generator import PdfGenerator
from .engine import DualRecord


class DominateReportMixin(HTMLReportMixin):
    _single = False

    @classmethod
    def body(cls, action, data, records):
        raise NotImplementedError

    @classmethod
    def title(cls, action, data, records):
        record = records[0] if records else None
        if record:
            return cls.label(record.raw.__name__)
        if action and action.model:
            return cls.label(action.model)
        return action.name if action else ''

    @classmethod
    def main(cls, action, data, records):
        body_nodes = cls.body(action, data, records)
        title = cls.title(action, data, records)
        if body_nodes is None:
            body_nodes = []
        if not isinstance(body_nodes, (list, tuple)):
            body_nodes = [body_nodes]
        return cls.build_document(action, data, records, title, body_nodes)

    @classmethod
    def header(cls, action, data, records):
        return None

    @classmethod
    def footer(cls, action, data, records):
        return None

    @classmethod
    def last_footer(cls, action, data, records):
        return None

    @classmethod
    def _render_node(cls, node):
        if node is None:
            return None
        return node.render() if hasattr(node, 'render') else str(node)

    @classmethod
    def css(cls, action, data, records):
        with file_open('html_report/base.css') as f:
            return f.read()

    @classmethod
    def build_document(cls, action, data, records, title, body_nodes):
        doc = document(title=title)
        doc['lang'] = 'en'
        with doc.head:
            meta(charset='utf-8')
            meta(name='description', content='')
            meta(name='author', content='Nantic')
            css = cls.css(action, data, records)
            if css:
                style(raw(css))
        with doc:
            doc.body['id'] = 'base'
            doc.body['class'] = 'main-report'
            for node in body_nodes:
                if node is None:
                    continue
                if isinstance(node, str):
                    doc.body.add(raw(node))
                else:
                    doc.body.add(node)
        return doc

    @classmethod
    def language(cls, records):
        return Transaction().language or 'en'

    @classmethod
    def _refresh_records(cls, records):
        for record in records:
            if isinstance(record, DualRecord):
                record.refresh()

    @classmethod
    def _execute_dominate_report(cls, records, data, action, side_margin=2,
            extra_vertical_margin=30):
        extension = data.get('output_format', action.extension or 'pdf')
        render_single = action.single or cls._single
        if render_single:
            documents = []
            for record in records:
                language = cls.language([record])
                with Transaction().set_context(language=language):
                    cls._refresh_records([record])
                    content = cls._render_node(cls.main(
                        action, data, [record]))
                    header = cls._render_node(cls.header(
                        action, data, [record]))
                    footer = cls._render_node(cls.footer(
                        action, data, [record]))
                    last_footer = cls._render_node(cls.last_footer(
                        action, data, [record]))

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
            language = cls.language(records)
            with Transaction().set_context(language=language):
                cls._refresh_records(records)
                content = cls._render_node(cls.main(
                    action, data, records))
                header = cls._render_node(cls.header(
                    action, data, records))
                footer = cls._render_node(cls.footer(
                    action, data, records))
                last_footer = cls._render_node(cls.last_footer(
                    action, data, records))
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
                        oext, rcontent = cls._execute_dominate_report(
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

            oext, content = cls._execute_dominate_report(
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
