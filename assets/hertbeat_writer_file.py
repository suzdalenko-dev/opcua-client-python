import json
import time
from datetime import datetime
import threading
from assets.conection_state_file import CONNECTION_STATE
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

            time.sleep(22)

            now = datetime.now()
            year_directory = JSONL_BASE_DIRECTORY / f"{now.year:04d}"
            year_directory.mkdir(parents=True, exist_ok=True, )
            moth_directory = JSONL_BASE_DIRECTORY / f"{now.year:04d}" / f"{now.month:04d}"
            moth_directory.mkdir(parents=True, exist_ok=True, )

            heartbeat_file_path = (moth_directory / HEARTBEAT_FILE_NAME)

            heartbeat = {"date": current_date()[:-4] , "conn": ("yes" if CONNECTION_STATE.is_connected() else "no"),}

            with open(heartbeat_file_path, "a", encoding="utf-8") as file:
                json.dump(heartbeat, file, ensure_ascii=False,)
                file.write("\n")

        except Exception as e:
            print(f"ERROR HEAD BIT {e}")

        

