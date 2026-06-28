import asyncio
import json
import os
from datetime import datetime
from assets.utils_file import current_date
from config import HEARTBEAT_FILE_NAME, HEARTBEAT_INTERVAL_SECONDS, JSONL_BASE_DIRECTORY,



HEARTBEAT_RETRY_SECONDS = 22


def overwrite_heartbeat_file(opcua_connected):
    """
    Sobrescribe completamente el archivo heartbeat.

    Ejemplo:
    ...2026/head-bit.json
    """
    now = datetime.now()
    year_directory = JSONL_BASE_DIRECTORY / f"{now.year:04d}"
    year_directory.mkdir(parents=True, exist_ok=True, )
    heartbeat_file_path = (year_directory / HEARTBEAT_FILE_NAME)
    temporary_file_path = (year_directory / f".{HEARTBEAT_FILE_NAME}.tmp")

    heartbeat = {
        "date": current_date(),
        "conn": ("yes" if opcua_connected else "no"),
    }

    # Primero se escribe un archivo temporal.
    with temporary_file_path.open(mode="w", encoding="utf-8",) as file:
        json.dump(heartbeat, file, ensure_ascii=False, separators=(",", ":"),)
        file.write("\n")

        # Envía el contenido desde el búfer de Python
        # al sistema operativo.
        file.flush()

        # Solicita al sistema operativo que persista
        # el contenido en disco.
        os.fsync(file.fileno(),)

    # Sustituye el archivo anterior de manera atómica.
    # Un lector nunca verá un JSON escrito a medias.
    os.replace(temporary_file_path, heartbeat_file_path,)



async def heartbeat_worker(connection_event, heartbeat_refresh_event,):
    """
    Escribe el heartbeat cada 22 segundos.
    También escribe inmediatamente cuando cambia
    el estado de la conexión OPC UA.
    """

    while True:
        # Limpiamos la señal antes de escribir.
        heartbeat_refresh_event.clear()

        try:
            await asyncio.to_thread(overwrite_heartbeat_file, connection_event.is_set(),)

        except asyncio.CancelledError:
            raise

        except Exception as error:
            print(
                "ERROR escribiendo heartbeat: "
                f"{error!r}",
                flush=True,
            )

            await asyncio.sleep(HEARTBEAT_RETRY_SECONDS,)
            continue

        try:
            # Espera hasta 22 segundos.
            #
            # Si la conexión cambia antes, el Event
            # despierta inmediatamente al worker.
            await asyncio.wait_for(heartbeat_refresh_event.wait(), timeout=HEARTBEAT_INTERVAL_SECONDS,)

        except TimeoutError:
            # Han pasado 22 segundos sin cambios.
            # El bucle vuelve a escribir normalmente.
            pass 