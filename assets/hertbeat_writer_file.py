import json
import shutil
import time
from datetime import datetime
import threading
from assets.conection_state_file import CONNECTION_STATE
import assets.database_file as database_file
import assets.app_recalculate_file as app_recalculate_file
from assets.utils_file import current_date
from config import HEARTBEAT_FILE_NAME, JSONL_BASE_DIRECTORY


def write_headbeat_log():
    thread = threading.Thread(target=write_heartbeat_file, daemon=True,)
    thread.start()


def write_heartbeat_file():
    while True:
        """
        Añade nueva linea en el archivo heartbeat.
        Ejemplo:
        ...2026/head-bit.json
        """
        try:
            time.sleep(2222)

            now = datetime.now()
            year_directory = JSONL_BASE_DIRECTORY / f"{now.year:04d}"
            year_directory.mkdir(parents=True, exist_ok=True, )


            heartbeat_file_path = year_directory / f"{now.month:02d}-{HEARTBEAT_FILE_NAME}"
            heartbeat = {
                "date"      : current_date(), 
                "conn"      : ("yes" if CONNECTION_STATE.is_connected() else "no"),
                "db_push"   : app_recalculate_file.DB_QUEUE_PUSH,
                "db_insert" : database_file.DB_INSERT_STATE,    
            }
            print(heartbeat)

            with open(heartbeat_file_path, "a", encoding="utf-8") as file:
                json.dump(heartbeat, file, ensure_ascii=False,)
                file.write("\n")


            year_ly = now.year - 1
            previous_year_directory = (JSONL_BASE_DIRECTORY / f"{year_ly:04d}")
            if previous_year_directory.exists():
                shutil.rmtree(previous_year_directory)
                print(f"Carpeta eliminada: {previous_year_directory}")



        except Exception as e:
            print(f"ERROR HEAD BIT {e}")

        

