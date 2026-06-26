import asyncio
from contextlib import suppress
from assets.connection import run_opcua_connection
from assets.exceptions import FatalServiceError
from assets.funcions.func import check_free_disk_space, file_writer, local_datetime_text, safe_write_health, set_fatal_error, wait_before_reconnect
from assets.funcions.func2 import stop_writer_normally
from config import EVENT_QUEUE_MAX_SIZE, RECONNECT_DELAY_SECONDS


async def run_service(stop_event,):
    """
    Bucle principal permanente del servicio.
    """
    event_queue   = asyncio.Queue(maxsize=EVENT_QUEUE_MAX_SIZE)
    fatal_event   = asyncio.Event()
    fatal_state   = {"message": "",}
    service_state = {"last_opc_ok": "",}
    writer_task = None

    try:
        free_disk_bytes = await asyncio.to_thread(check_free_disk_space)
        

        safe_write_health(
            status="starting",
            queue_size=0,
            last_opc_ok="",
            free_disk_bytes=free_disk_bytes,
        )

        writer_task = asyncio.create_task(
            file_writer(event_queue=event_queue, fatal_event=fatal_event, fatal_state=fatal_state,)
        )

        while not stop_event.is_set():
            if fatal_event.is_set():
                raise FatalServiceError(
                    fatal_state.get(
                        "message",
                        "Error fatal desconocido.",
                    )
                )

            if writer_task.done():
                set_fatal_error(
                    fatal_event=fatal_event,
                    fatal_state=fatal_state,
                    message=(
                        "El escritor de archivos "
                        "ha terminado inesperadamente."
                    ),
                )

                raise FatalServiceError(
                    fatal_state["message"]
                )

            try:
                await run_opcua_connection(
                    stop_event=stop_event,
                    event_queue=event_queue,
                    fatal_event=fatal_event,
                    fatal_state=fatal_state,
                    service_state=service_state,
                )

            except asyncio.CancelledError:
                raise

            except FatalServiceError as error:
                set_fatal_error(
                    fatal_event=fatal_event,
                    fatal_state=fatal_state,
                    message=str(error),
                )

                raise

            except Exception as error:
                if stop_event.is_set():
                    break

                if fatal_event.is_set():
                    raise FatalServiceError(
                        fatal_state.get("message", str(error),)
                    )

                print(
                    f"{local_datetime_text(milliseconds=False)} "
                    f"[ERROR OPC UA] "
                    f"{error!r}"
                )

                print(
                    "Se intentará reconectar "
                    f"dentro de "
                    f"{RECONNECT_DELAY_SECONDS} "
                    "segundos."
                )

                safe_write_health(
                    status="reconnecting",
                    detail=repr(
                        error
                    ),
                    queue_size=(
                        event_queue.qsize()
                    ),
                    last_opc_ok=(
                        service_state[
                            "last_opc_ok"
                        ]
                    ),
                )

                await wait_before_reconnect(stop_event=stop_event)

    except asyncio.CancelledError:
        raise

    except Exception as error:
        set_fatal_error(
            fatal_event=fatal_event,
            fatal_state=fatal_state,
            message=str(error),
        )

        raise

    finally:
        if writer_task is not None:
            if fatal_event.is_set():
                if not writer_task.done():
                    writer_task.cancel()

                with suppress(
                    asyncio.CancelledError,
                    Exception,
                ):
                    await writer_task

                safe_write_health(
                    status="fatal",
                    detail=(
                        fatal_state.get(
                            "message",
                            "Error fatal.",
                        )
                    ),
                    queue_size=(
                        event_queue.qsize()
                    ),
                    last_opc_ok=(
                        service_state[
                            "last_opc_ok"
                        ]
                    ),
                )

            else:
                safe_write_health(
                    status="stopping",
                    queue_size=(
                        event_queue.qsize()
                    ),
                    last_opc_ok=(
                        service_state[
                            "last_opc_ok"
                        ]
                    ),
                )

                try:
                    await stop_writer_normally(event_queue=event_queue, writer_task=writer_task,)

                except asyncio.TimeoutError:
                    print(
                        f"{local_datetime_text(milliseconds=False)} "
                        "[ERROR] No se pudo vaciar "
                        "la cola dentro del tiempo máximo."
                    )

                    if not writer_task.done():
                        writer_task.cancel()

                    with suppress(
                        asyncio.CancelledError,
                        Exception,
                    ):
                        await writer_task

                safe_write_health(
                    status="stopped",
                    queue_size=(
                        event_queue.qsize()
                    ),
                    last_opc_ok=(
                        service_state[
                            "last_opc_ok"
                        ]
                    ),
                )