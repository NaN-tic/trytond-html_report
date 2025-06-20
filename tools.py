import tempfile
from openpyxl.writer.excel import save_workbook
from datetime import date, datetime, time as dt_time
from decimal import Decimal

def save_virtual_workbook(workbook):
    with tempfile.NamedTemporaryFile() as tmp:
        save_workbook(workbook, tmp.name)
        with open(tmp.name, 'rb') as f:
            return f.read()

def _convert_to_title(value):
    # Replace symbols that are not allowed in the sheet name
    title = value.replace('/', '_').replace(':', '_')
    # Excel has a limit of 31 characters for the sheet name
    title = title[:31]
    return title

def _convert_to_string(value):
    if isinstance(value, (Decimal, str, int, float, date, datetime,
            dt_time, bool)):
        return value
    return str(value) if value is not None else None

def _convert_str_to_float(value):
    if isinstance(value, str):
        try:
            return float(value.replace(',', '.'))
        except ValueError:
            return value
    return value
