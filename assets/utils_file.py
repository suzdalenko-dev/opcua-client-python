from datetime import datetime



def current_date():
    date_format    = "%Y-%m-%d %H:%M:%S"
    current_date   = datetime.now().strftime(date_format)   # [:-3]
    return current_date



def format_datetime(date_value):
    """
    Convierte un datetime a un string:

    YYYY-MM-DD HH:MM:SS

    Mantiene la fecha y hora tal como vienen.
    """
    DATE_FORMAT_SECONDS = "%Y-%m-%d %H:%M:%S.%f"

    if date_value is None:
        return None

    if not isinstance(date_value, datetime):
        return ""

    return date_value.strftime(DATE_FORMAT_SECONDS,)[:-3] 



def value_to_number(value):
    """Convierte '  3479.454' o '3364' a float/int; si no, deja el texto."""
    try:
        texto = str(value).strip().rstrip("G").strip()
        return float(texto)
    except (ValueError, TypeError):
        return value
 