import asyncio, queue

# Consumida por jsonl_writer(), que funciona con asyncio.
EVENT_QUEUE = asyncio.Queue(maxsize=50_000,)

# Consumida por el hilo que escribe estadísticas.
STATS_QUEUE = queue.Queue(maxsize=50_000,)

# Consumida exclusivamente por el hilo PostgreSQL.
DB_QUEUE = queue.Queue(maxsize=50_000,)