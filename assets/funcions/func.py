import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from assets.exceptions import FatalServiceError
from assets.funcions.func2 import local_datetime_text
from assets.funcions.func3 import get_free_disk_bytes, safe_write_health
from config import (
    DISK_RETRY_SECONDS,
    DISK_WRITE_MAX_RETRIES,
    LOG_DIRECTORY,
    MIN_FREE_DISK_BYTES,
    RECONNECT_DELAY_SECONDS,
    STAT_TAGS,
    WATCHDOG_INTERVAL_SECONDS,
    WATCHDOG_READ_TIMEOUT_SECONDS,
)



def normalize_timestamp(value,):
    """
    Convierte el timestamp OPC UA a:

        YYYY-MM-DD HH:MM:SS.mmm
    """
    if value is None:
        return ""

    if not isinstance(value, datetime,):
        return str(value)

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]



def status_is_good(status_code,):
    """
    Devuelve True cuando el estado OPC UA
    indica que el valor es correcto.
    """
    if status_code is None:
        return False

    try:
        return bool(status_code.is_good())

    except (AttributeError,TypeError,):
        pass

    status_value = getattr(status_code, "value", None,)

    if status_value is not None:
        try:
            return int(status_value) == 0

        except (TypeError,ValueError,):
            pass

    return str(status_code) in ("Good","StatusCode(value=0)",)



def get_year_directory(moment,):
    """
    Ejemplo:
        /var/lib/froxa-opcua/2026/
    """
    directory = (Path(LOG_DIRECTORY) / moment.strftime("%Y"))
    directory.mkdir(parents=True, exist_ok=True,)
    return directory



def get_all_file_path(moment,):
    """
    Archivo que contiene todos los tags.
    Ejemplo:
        /var/lib/froxa-opcua/2026/06-all.jsonl
    """
    directory = get_year_directory(moment)
    return directory / (f"{moment:%m}-all.jsonl")



def get_stat_file_path(moment,):
    """
    Archivo que contiene únicamente
    los tags definidos en TAGS.
    Ejemplo:
        /var/lib/froxa-opcua/2026/06-static.jsonl
    """
    directory = get_year_directory(moment)
    return directory / (f"{moment:%m}-static.jsonl")



def check_free_disk_space():
    """
    Comprueba que queda suficiente espacio
    libre en la partición.
    """
    free_disk_bytes = (get_free_disk_bytes())

    if (free_disk_bytes < MIN_FREE_DISK_BYTES):
        free_disk_mb = (free_disk_bytes / 1024 / 1024)
        minimum_disk_mb = (MIN_FREE_DISK_BYTES / 1024 / 1024)

        raise FatalServiceError(f"Espacio libre insuficiente: {free_disk_mb:.2f} MB. El mínimo configurado es {minimum_disk_mb:.2f} MB.")
    return free_disk_bytes






def append_json_line(file_path, record,):
    """
    Añade una línea JSON y fuerza su escritura
    física en disco.
    """
    json_line = (json.dumps(record, ensure_ascii=False, separators=(",", ":"),) + "\n")

    with file_path.open("a", encoding="utf-8",) as file:
        file.write(json_line)
        file.flush()
        os.fsync(file.fileno())



def set_fatal_error(fatal_event, fatal_state, message,):
    """
    Registra únicamente el primer error fatal.
    """
    if fatal_event.is_set():
        return
    fatal_state["message"] = str(message)
    print(
        f"{local_datetime_text(milliseconds=False)} "
        f"[ERROR FATAL] "
        f"{message}"
    )
    fatal_event.set()






async def write_record_to_file(file_path, record, fatal_event, fatal_state,):
    """
    Escribe un registro en un archivo concreto.

    Si falla MM-stat.json, solamente vuelve
    a intentar MM-stat.json.

    No vuelve a escribir la línea que ya se
    guardó correctamente en MM-all.json.
    """
    for attempt in range(1, DISK_WRITE_MAX_RETRIES + 1,):
        try:
            await asyncio.to_thread(append_json_line, file_path, record,)
            return True
        except asyncio.CancelledError:
            raise

        except Exception as error:
            if (attempt >= DISK_WRITE_MAX_RETRIES):
                set_fatal_error(
                    fatal_event=fatal_event,
                    fatal_state=fatal_state,
                    message=(
                        "No se puede escribir en "
                        f"{file_path} después de "
                        f"{attempt} intentos: "
                        f"{error!r}"
                    ),
                )

                return False

            print(
                f"{local_datetime_text(milliseconds=False)} "
                f"[ERROR DISCO] "
                f"{file_path} "
                f"intento {attempt}/"
                f"{DISK_WRITE_MAX_RETRIES}: "
                f"{error!r}"
            )

            await asyncio.sleep(DISK_RETRY_SECONDS)

    return False



async def file_writer(event_queue, fatal_event, fatal_state,):
    """
    Único escritor de los archivos mensuales.
    Todos los eventos se guardan en:
        MM-all.json
    Los eventos de TAGS también se guardan en:
        MM-stat.json
    """
    try:
        while True:
            item = await event_queue.get()

            try:
                if item is None:
                    return

                record = item["record"]
                file_paths = item["file_paths"]

                for file_path in file_paths:
                    saved = (
                        await write_record_to_file(
                            file_path=file_path,
                            record=record,
                            fatal_event=fatal_event,
                            fatal_state=fatal_state,
                        )
                    )

                    if not saved:
                        return

            finally:
                event_queue.task_done()

    except asyncio.CancelledError:
        raise

    except Exception as error:
        set_fatal_error(
            fatal_event=fatal_event,
            fatal_state=fatal_state,
            message=(
                "El escritor de archivos "
                f"ha fallado: {error!r}"
            ),
        )



def create_queue_item(tag, value, source_timestamp, status_code,):
    """
    Crea el registro y determina en qué
    archivos debe guardarse.
    Todos los tags:
        MM-all.jsonl
    Tags incluidos en TAGS:
        MM-all.jsonl
        MM-static.jsonl
    """
    received_at = (datetime.now().astimezone())

    record = {
        "received": (local_datetime_text(received_at)),
        "timestamp": (normalize_timestamp(source_timestamp)),
        "tag": tag,
        "value": ("" if value is None else str(value)),
    }

    # Los valores correctos no incluyen
    # ningún campo adicional.
    #
    # Solo se registra el estado cuando
    # OPC UA devuelve Bad o Uncertain.
    if not status_is_good(status_code):

        record["status"] = str(status_code)

    file_paths = [get_all_file_path(received_at),]

    if tag in STAT_TAGS:
        file_paths.append(get_stat_file_path(received_at))

    return {
        "file_paths": file_paths,
        "record": record,
    }



async def connection_watchdog(node, stop_event, event_queue, service_state,):
    """
    Comprueba periódicamente:

    - Que OPC UA responde.
    - Que queda suficiente espacio en disco.
    - Que health.json se actualiza.
    """
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=WATCHDOG_INTERVAL_SECONDS,)
            return

        except asyncio.TimeoutError:
            pass

        await asyncio.wait_for(
            node.read_value(),
            timeout=WATCHDOG_READ_TIMEOUT_SECONDS,
        )

        free_disk_bytes = (
            await asyncio.to_thread(check_free_disk_space)
        )

        service_state["last_opc_ok"] = (local_datetime_text())
        safe_write_health(
            status="connected",
            queue_size=(event_queue.qsize()),
            last_opc_ok=(service_state["last_opc_ok"]),
            free_disk_bytes=(free_disk_bytes),
        )



async def wait_before_reconnect(stop_event,):
    """
    Espera antes de reconectar y permite
    detener inmediatamente el servicio.
    """
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=RECONNECT_DELAY_SECONDS,)

    except asyncio.TimeoutError:
        pass




