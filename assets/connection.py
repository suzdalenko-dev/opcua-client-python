import asyncio
from contextlib import suppress
from asyncua import Client
from assets.exceptions import FatalServiceError
from assets.funcions.func import check_free_disk_space, connection_watchdog, local_datetime_text, safe_write_health
from assets.suscription_handler import SubscriptionHandler
from config import ALL_TAGS, MONITORED_ITEM_QUEUE_SIZE, NODE_ID_PREFIX, READ_TAGS_TIME_MS, URL


async def run_opcua_connection(stop_event, event_queue, fatal_event, fatal_state, service_state,):
    """
    Mantiene una conexión OPC UA activa hasta
    recibir una parada, una caída de conexión
    o un error fatal.
    """
    print(f"Conectando con {URL}...")

    safe_write_health(
        status="connecting",
        queue_size=event_queue.qsize(),
        last_opc_ok=service_state["last_opc_ok"],
    )

    async with Client(url=URL, timeout=10,) as client:
        print("Conexión OPC UA correcta")

        nodes_by_tag = {
            tag: client.get_node(f"{NODE_ID_PREFIX}{tag}")
            for tag in ALL_TAGS
        }

        tag_by_node_id = {
            node.nodeid.to_string(): tag
            for tag, node
            in nodes_by_tag.items()
        }

        handler = SubscriptionHandler(
            tag_by_node_id=tag_by_node_id,
            event_queue=event_queue,
            fatal_event=fatal_event,
            fatal_state=fatal_state,
        )

        subscription = (
            await client.create_subscription(READ_TAGS_TIME_MS, handler,)
        )

        await subscription.subscribe_data_change(
            list(nodes_by_tag.values()),
            queuesize=MONITORED_ITEM_QUEUE_SIZE,
            sampling_interval=READ_TAGS_TIME_MS,
        )

        service_state["last_opc_ok"] = local_datetime_text()
    
        free_disk_bytes = await asyncio.to_thread(check_free_disk_space)
        

        safe_write_health(
            status="connected",
            queue_size=event_queue.qsize(),
            last_opc_ok=service_state["last_opc_ok"],
            free_disk_bytes=free_disk_bytes,
        )

        stop_task     = asyncio.create_task(stop_event.wait())
        fatal_task    = asyncio.create_task(fatal_event.wait())
        watchdog_node = nodes_by_tag.get("STAG00")
        

        if watchdog_node is None:
            watchdog_node = next(
                iter(nodes_by_tag.values())
            )

        watchdog_task = asyncio.create_task(
            connection_watchdog(
                node=watchdog_node,
                stop_event=stop_event,
                event_queue=event_queue,
                service_state=service_state,
            )
        )

        tasks = (
            stop_task,
            fatal_task,
            watchdog_task,
        )

        try:
            completed_tasks, _ = (
                await asyncio.wait(
                    tasks,
                    return_when=(
                        asyncio.FIRST_COMPLETED
                    ),
                )
            )

            if fatal_task in completed_tasks:
                raise FatalServiceError(
                    fatal_state.get(
                        "message",
                        "Error fatal desconocido.",
                    )
                )

            if watchdog_task in completed_tasks:
                await watchdog_task

        finally:
            handler.active = False

            for task in tasks:
                if not task.done():
                    task.cancel()

            for task in tasks:
                with suppress(
                    asyncio.CancelledError,
                    Exception,
                ):
                    await task

            with suppress(
                asyncio.CancelledError,
                Exception,
            ):
                await asyncio.wait_for(
                    subscription.delete(),
                    timeout=5,
                )

