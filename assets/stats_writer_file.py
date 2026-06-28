from datetime import datetime
import json
import threading
import time
from assets.event_queue_file import STATS_QUEUE
from config import JSONL_BASE_DIRECTORY


def start_stats_writer():
    '''
    Solo arranca 1 vez
    '''
    tread = threading.Thread(target=_stats_writer_loop, daemon=True)
    tread.start()
    return tread


def _append_stats(event):
    now = datetime.now()
    year_directory = JSONL_BASE_DIRECTORY / f"{now.year:04d}"
    year_directory.mkdir(parents=True, exist_ok=True)
    file_path = year_directory / f"{now.month:02d}-stats.json"
    json_line = json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str)
    
    with file_path.open(mode="a", encoding="utf-8") as file:
        file.write(json_line)
        file.write("\n")
        file.flush()


def _stats_writer_loop():
    while True:
        event = STATS_QUEUE.get()
        try:
            while True:
                try:
                    _append_stats(event)
                    break
                except Exception as e:
                    time.sleep(5)
        finally:
            STATS_QUEUE.task_done()