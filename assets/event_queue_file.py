import asyncio, queue

# Consumida por jsonl_writer(), que funciona con asyncio.
EVENT_QUEUE = asyncio.Queue(maxsize=50_000,)

# Consumida por el hilo que escribe estadísticas.
STATS_QUEUE = queue.Queue(maxsize=50_000,)

# Consumida exclusivamente por el hilo PostgreSQL.
DB_QUEUE = queue.Queue(maxsize=50_000,)



'''
A ver si entiendo el ciclo de vida de 
    EVENT_QUEUE = asyncio.Queue(maxsize=50_000,)

async def worker(queue):
    while True:
        item = await queue.get()

        try:
            print(f"Procesando: {item}")
            await asyncio.sleep(1)

        finally:
            queue.task_done()


async def main():
    queue = asyncio.Queue()

    worker_task = asyncio.create_task(worker(queue),)

    await queue.put("evento 1")
    await queue.put("evento 2")
    await queue.put("evento 3")

    # Espera a que los tres eventos hayan terminado.
    await queue.join()

    print("Todos los eventos procesados")

    worker_task.cancel()


asyncio.run(main())
'''