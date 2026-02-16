from dominate.util import raw

from trytond.pool import Pool, PoolMeta

from .dominate import DominateJinjaRenderer


class Company(metaclass=PoolMeta):
    __name__ = 'company.company'

    @classmethod
    def _get_action_report(cls, name=None):
        if not name:
            return None
        ActionReport = Pool().get('ir.action.report')
        reports = ActionReport.search([('report_name', '=', name)], limit=1)
        return reports[0] if reports else None

    def dominate_header(self, name=None, record=None, records=None, data=None):
        action = self._get_action_report(name)
        if action and action.html_header_content:
            return DominateJinjaRenderer.render_template(
                action,
                action.html_header_content,
                record=record,
                records=records,
                data=data,
            )
        return raw(self.header or '')

    def dominate_footer(self, name=None, record=None, records=None, data=None):
        action = self._get_action_report(name)
        if action and action.html_footer_content:
            return DominateJinjaRenderer.render_template(
                action,
                action.html_footer_content,
                record=record,
                records=records,
                data=data,
            )
        return raw(self.footer or '')

    def dominate_last_footer(self, name=None, record=None, records=None,
            data=None):
        action = self._get_action_report(name)
        if action and action.html_last_footer_content:
            return DominateJinjaRenderer.render_template(
                action,
                action.html_last_footer_content,
                record=record,
                records=records,
                data=data,
            )
        return raw('')

    def dominate_macro(self, signature_name, name=None, record=None,
            records=None, data=None):
        action = self._get_action_report(name)
        return DominateJinjaRenderer.render_macro(
            action,
            signature_name,
            record=record,
            records=records,
            data=data,
        )
