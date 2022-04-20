# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from io import StringIO, BytesIO
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction
from babel.messages.extract import extract as babel_extract
import jinja2

__all__ = ['ReportTranslationSet']


class ReportTranslationSet(metaclass=PoolMeta):
    __name__ = "ir.translation.set"

    def set_report(self):
        super().set_report()
        self.extract_translation_jinja()

    def extract_report_jinja(self, content):
        # TODO extract .po files
        return []

    def extract_translation_jinja(self):
        pool = Pool()
        Translation = pool.get('html.template.translation')
        Report = pool.get('ir.action.report')
        Lang = Pool().get('ir.lang')

        context = Transaction().context
        if context.get('active_ids'):
            reports = Report.browse(context.get('active_ids'))
            reports = [x for x in reports if x.template_extension == 'jinja']
            if not reports:
                return
        else:
            return

        translations = Translation.search([('report', 'in',
            [x.id for x in reports])])

        def get_messages(content):
            res = set()
            st = StringIO(content)
            by = BytesIO(st.read().encode('utf-8'))
            messages = babel_extract(jinja2.ext.babel_extract, by)
            for message in messages:
                res.add(message[1])
            return list(res)

        key2ids = {}
        for translation in translations:
            key = translation.unique_key
            key2ids.setdefault(key, []).append(translation.id)

        messages = []
        for report in reports:
            messages += get_messages(report.html_content)
            messages += get_messages(report.html_header_content)
            messages += get_messages(report.html_footer_content)

        langs = Lang.search([
            ('translatable', '=', True),
            ('code', '!=', 'en'),
            ])
        to_save = []
        for message in messages:
            for lang in langs:
                # translation.unique_key
                key = (message, lang.code)
                if key in key2ids:
                    continue
                translation = Translation(report=report, src=message,
                    lang=lang.code)
                to_save.append(translation)

        Translation.save(to_save)
