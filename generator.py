from weasyprint import HTML, CSS
from trytond.i18n import gettext
from trytond.exceptions import UserError
from trytond.transaction import Transaction
import os
import json
import tempfile
import subprocess

class PdfGenerator:
    """
    Generate a PDF out of a rendered template, with the possibility to
    integrate nicely a header and a footer if provided.

    Notes:
    ------
    - When Weasyprint renders an html into a PDF, it goes though several
      intermediate steps. Here, in this class, we deal mostly with a box
      representation: 1 `Document` have 1 `Page` or more, each `Page` 1 `Box`
      or more. Each box can contain other box. Hence the recursive method
      `get_element` for example.
      For more, see:
      https://weasyprint.readthedocs.io/en/stable/hacking.html#dive-into-the-source
      https://weasyprint.readthedocs.io/en/stable/hacking.html#formatting-structure
    - Warning: the logic of this class relies heavily on the internal
      Weasyprint API. This snippet was written at the time of the release 47,
      it might break in the future.
    - This generator draws its inspiration and, also a bit of its
      implementation, from this discussion in the library github issues:
        https://github.com/Kozea/WeasyPrint/issues/92
    """
    OVERLAY_LAYOUT = '@page {size: A4 portrait; margin: 0;}'

    def __init__(self, main_html, header_html=None, footer_html=None,
            last_footer_html=None, base_url=None, side_margin=2,
            extra_vertical_margin=30):
        """
        Parameters
        ----------
        main_html: str
            An HTML file (most of the time a template rendered into a string)
            which represents the core of the PDF to generate.
        header_html: str
            An optional header html.
        footer_html: str
            An optional footer html.
        base_url: str
            An absolute url to the page which serves as a reference to
            Weasyprint to fetch assets, required to get our media.
        side_margin: int, interpreted in cm, by default 2cm
            The margin to apply on the core of the rendered PDF
            (i.e. main_html).
        extra_vertical_margin: int, interpreted in pixel, by default 30 pixels
            An extra margin to apply between the main content and header and
            the footer.
            The goal is to avoid having the content of `main_html` touching the
            header or the footer.
        """
        self.main_html = main_html
        self.header_html = header_html
        self.footer_html = footer_html
        self.last_footer_html = last_footer_html
        self.base_url = base_url
        self.side_margin = side_margin
        self.extra_vertical_margin = extra_vertical_margin

    def _compute_overlay_element(self, element: str):
        """
        Parameters
        ----------
        element: str
            Either 'header' or 'footer'

        Returns
        -------
        element_body: BlockBox
            A Weasyprint pre-rendered representation of an html element
        element_height: float
            The height of this element, which will be then translated in a html
            height
        """
        html = HTML(
            string=getattr(self, '{}_html'.format(element)).replace('\n', ''),
            base_url=self.base_url,
            )
        element_doc = html.render(
            stylesheets=[CSS(string=self.OVERLAY_LAYOUT)])
        element_page = element_doc.pages[0]
        element_body = PdfGenerator.get_element(
            element_page._page_box.all_children(), 'body')
        element_body = element_body.copy_with_children(
            element_body.all_children())
        element_html = PdfGenerator.get_element(
            element_page._page_box.all_children(), element.replace('_', '-'))

        if element == 'header':
            if element_html:
                element_height = element_html.height
            else:
                element_height = 0
        if element == 'footer':
            if element_html:
                element_height = element_page.height - element_html.position_y
            else:
                element_height = element_page.height
        if element == 'last_footer':
            if element_html:
                element_height = (element_page.height - element_html.position_y
                    - element_html.margin_bottom)
            else:
                element_height = element_page.height

        return element_body, element_height

    def _apply_overlay_on_main(self, main_doc, header_body=None,
            footer_body=None, last_footer_body=None):
        """
        Insert the header and the footer in the main document.

        Parameters
        ----------
        main_doc: Document
            The top level representation for a PDF page in Weasyprint.
        header_body: BlockBox
            A representation for an html element in Weasyprint.
        footer_body: BlockBox
            A representation for an html element in Weasyprint.
        last_footer_body: BlockBox
            A representation for an html element in Weasyprint.
        """

        total_pages = len(main_doc.pages)
        number_page = 1
        for page in main_doc.pages:
            page_body = PdfGenerator.get_element(page._page_box.all_children(),
                'body')

            if header_body:
                page_body.children += header_body.all_children()
            if last_footer_body and number_page == total_pages:
                page_body.children += last_footer_body.all_children()
            if footer_body:
                page_body.children += footer_body.all_children()
            number_page += 1

    def render_html(self):
        """
        Returns
        -------
        pdf: a bytes sequence
            The rendered PDF.
        """
        if self.header_html:
            header_body, header_height = self._compute_overlay_element(
                'header')
        else:
            header_body, header_height = None, 0
        if self.footer_html:
            footer_body, footer_height = self._compute_overlay_element(
                'footer')
        else:
            footer_body, footer_height = None, 0
        if self.last_footer_html:
            last_footer_body, last_footer_height = (
                self._compute_overlay_element('last_footer'))
        else:
            last_footer_body, last_footer_height = None, 0
        footer_height += last_footer_height

        margins = '{header_size}px {side_margin} {footer_size}px\
            {side_margin}'.format(
            header_size=header_height + self.extra_vertical_margin,
            footer_size=footer_height + self.extra_vertical_margin,
            side_margin='{}cm'.format(self.side_margin),
            )
        content_print_layout = ('@page {size: A4 portrait; margin: %s;}'
            % margins)

        html = HTML(
            string=self.main_html,
            base_url=self.base_url,
        )
        main_doc = html.render(stylesheets=[CSS(string=content_print_layout)])

        if self.header_html or self.footer_html or self.last_footer_html:
            self._apply_overlay_on_main(main_doc, header_body, footer_body,
                last_footer_body)

        return main_doc

    def render_pdf(self):
        context = Transaction().context
        timeout_report = context.get('timeout_report', None)
        if timeout_report > 1000000:
            # Python does not allow a timeout greater than 1000000 seconds (at
            # least it does not allow an order of magnitude larger than that)
            # That is more than 11 days so it should not be a problem
            timeout_report = 1000000

        if timeout_report:
            path = os.path.dirname(os.path.abspath(__file__)) + '/'
            json_path = self.to_json_file()
            process = subprocess.Popen(['python3', path+'generator_script.py', json_path],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        encoding='utf-8', errors='ignore')
            out = None
            try:
                out, err = process.communicate(timeout=timeout_report)
            except subprocess.TimeoutExpired:
                process.kill()
                out, err = process.communicate()
                raise UserError(gettext('html_report.msg_error_timeout', seconds=timeout_report))
            finally:
                os.remove(json_path)

            document = None
            if out and os.path.exists(out.strip()):
                with open(out.strip(), 'rb') as file:
                    document = file.read()
                os.remove(out.strip())
        else:
            document = self.render_html().write_pdf()
        return document

    @staticmethod
    def get_element(boxes, element):
        """
        Given a set of boxes representing the elements of a PDF page in a
        DOM-like way, find the box which is named `element`.

        Look at the notes of the class for more details on Weasyprint insides.
        """
        for box in boxes:
            if box.element_tag == element:
                return box
            box_children = PdfGenerator.get_element(box.all_children(), element)
            if box_children:
                return box_children

    def to_json_file(self):
        """
        Write the PdfGenerator properties to a JSON file.

        Parameters:
        - filepath: The path to the JSON file.
        """
        data = {
            "main_html": self.main_html,
            "header_html": self.header_html,
            "footer_html": self.footer_html,
            "last_footer_html": self.last_footer_html,
            "base_url": self.base_url,
            "side_margin": self.side_margin,
            "extra_vertical_margin": self.extra_vertical_margin
        }
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as file:
            filepath = file.name
            json.dump(data, file)
        return filepath
