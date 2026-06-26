import json
import os
from pathlib import Path
import shutil

from assets.funcions.func2 import local_datetime_text
from config import LOG_DIRECTORY


def get_health_file_path():
    """
    Ruta del archivo de estado del servicio.
    Ejemplo:
        /var/lib/froxa-opcua/health.json
    """
    directory = Path(LOG_DIRECTORY)
    directory.mkdir(parents=True, exist_ok=True,)
    return directory / "health.json"



def get_free_disk_bytes():
    """
    Devuelve el espacio libre (en bytes) de la
    partición donde se guardan los datos.
    """
    directory = Path(LOG_DIRECTORY)
    directory.mkdir(parents=True, exist_ok=True,)
    return shutil.disk_usage(directory).free



def safe_write_health(status, detail="", queue_size=0, last_opc_ok="", free_disk_bytes=None,):
    """
    Actualiza health.json sin permitir que
    un fallo de este archivo cierre el servicio.
    """
    try:
        write_health(
            status=status,
            detail=detail,
            queue_size=queue_size,
            last_opc_ok=last_opc_ok,
            free_disk_bytes=free_disk_bytes,
        )
    except Exception as error:
        print(
            f"{local_datetime_text(milliseconds=False)} "
            f"[ERROR HEALTH] "
            f"{error!r}"
        )



def write_health(status, detail="", queue_size=0, last_opc_ok="", free_disk_bytes=None,):
    """
    Escribe health.json mediante reemplazo
    atómico para evitar dejarlo incompleto.
    """
    file_path = (get_health_file_path())
    temporary_file_path = (file_path.with_name(f".{file_path.name}.tmp"))

    if free_disk_bytes is None:
        try:
            free_disk_bytes = (get_free_disk_bytes())
        except Exception:
            free_disk_bytes = None

    record = {
        "updated_at": (local_datetime_text()),
        "status": status,
        "queue_size": queue_size,
        "last_opc_ok": last_opc_ok,
    }

    if detail:
        record["detail"] = detail

    if free_disk_bytes is not None:
        record["free_disk_mb"] = round(free_disk_bytes / 1024 / 1024, 2,)

    with temporary_file_path.open("w", encoding="utf-8",) as file:
        json.dump(record, file, ensure_ascii=False, separators=(",", ":"),)
        file.write( "\n")
        file.flush()
        os.fsync(file.fileno())

    os.replace(temporary_file_path, file_path,)
