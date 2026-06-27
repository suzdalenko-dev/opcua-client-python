from datetime import datetime
from zoneinfo import ZoneInfo


def current_date():
    date_format    = "%Y-%m-%d %H:%M:%S.%f"
    current_date   = datetime.now().strftime(date_format[:-5])
    return current_date



def format_datetime(date_value):
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    """
    Convierte un datetime a un string con formato:

    YYYY-MM-DD HH:MM:SS

    Si recibe None, devuelve None.
    """
    if date_value is None:
        return None

    if not isinstance(date_value, datetime):
        return ""


    return date_value.strftime(DATE_FORMAT)