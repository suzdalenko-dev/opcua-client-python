"""
Almacenamiento en disco.

Responsabilidad UNICA de este modulo: convertir un dato leido del
equipo en un registro y guardarlo en los archivos correspondientes.

Se guardan dos archivos diarios:
    <LOG_DIRECTORY>/todas/AAAA/MM/AAAA-MM-DD.jsonl  -> TODOS los tags
    <LOG_DIRECTORY>/tags/AAAA/MM/AAAA-MM-DD.jsonl   -> solo los de TAGS
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path

from config import LOG_DIRECTORY, STAT_TAGS


# Carpetas de los dos archivos.
TODAS_DIRECTORY = Path(LOG_DIRECTORY) / "todas"
TAGS_DIRECTORY = Path(LOG_DIRECTORY) / "tags"

# Tags cuyo valor es una fecha de maquina 'AAAA/MM/DD HH:MM:SS'.
DATETIME_TAGS = ("STAG25", "STAG26")


def _normalizar_timestamp(value):
    if value is None:
        return ""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _normalizar_fecha_maquina(value):
    # STAG25/STAG26 llegan como 'AAAA/MM/DD HH:MM:SS'.
    # Pasamos los separadores a guiones -> 'AAAA-MM-DD HH:MM:SS'.
    if value is None:
        return ""

    return str(value).strip().replace("/", "-")


def _ruta_diaria(base_directory, moment):
    directory = base_directory / moment.strftime("%Y") / moment.strftime("%m")
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{moment:%Y-%m-%d}.jsonl"


def _anadir_linea(file_path, record):
    # Escribe una linea y la fuerza a disco (fsync) para no perder
    # datos ante un corte de luz o un apagado brusco.
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"

    with file_path.open("a", encoding="utf-8") as file:
        file.write(line)
        file.flush()
        os.fsync(file.fileno())


def guardar(tag, value, node_id, source_timestamp, server_timestamp, status_code, variant_type):
    """Construye el registro y lo guarda en los archivos que correspondan."""
    received_at = datetime.now().astimezone()

    if tag in DATETIME_TAGS:
        value = _normalizar_fecha_maquina(value)

    record = {
        "received_at": received_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "source_timestamp": _normalizar_timestamp(source_timestamp),
        "server_timestamp": _normalizar_timestamp(server_timestamp),
        "tag": tag,
        "value": "" if value is None else str(value),
        "node_id": node_id,
        "status_code": status_code,
        "variant_type": variant_type,
    }

    # Archivo 1: TODAS las lecturas.
    _anadir_linea(_ruta_diaria(TODAS_DIRECTORY, received_at), record)

    # Archivo 2: solo los tags de TAGS.
    if tag in STAT_TAGS:
        _anadir_linea(_ruta_diaria(TAGS_DIRECTORY, received_at), record)
