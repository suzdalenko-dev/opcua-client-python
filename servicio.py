"""
Servicio OPC UA.

Responsabilidad UNICA de este modulo: conectar con el equipo, crear la
suscripcion a todos los tags y mantenerla activa hasta que se pida parar.
No sabe como se guardan los datos (de eso se encarga el manejador).
"""

from asyncua import Client

from config import (
    ALL_TAGS,
    MONITORED_ITEM_QUEUE_SIZE,
    NODE_ID_PREFIX,
    READ_TAGS_TIME_MS,
    STAT_TAGS,
    URL,
)
from suscripcion import ManejadorSuscripcion


async def ejecutar(stop_event):
    """Conecta, suscribe y espera hasta que stop_event se active."""
    print(f"Conectando con {URL}...")

    async with Client(url=URL, timeout=10) as client:
        print("Conexion OPC UA correcta")

        nodos_por_tag = {
            tag: client.get_node(f"{NODE_ID_PREFIX}{tag}")
            for tag in ALL_TAGS
        }

        tag_por_node_id = {
            node.nodeid.to_string(): tag
            for tag, node in nodos_por_tag.items()
        }

        manejador = ManejadorSuscripcion(tag_por_node_id=tag_por_node_id)

        suscripcion = await client.create_subscription(READ_TAGS_TIME_MS, manejador)

        await suscripcion.subscribe_data_change(
            list(nodos_por_tag.values()),
            queuesize=MONITORED_ITEM_QUEUE_SIZE,
            sampling_interval=READ_TAGS_TIME_MS,
        )

        print(
            f"Suscripcion creada para {len(ALL_TAGS)} tags "
            f"({len(STAT_TAGS)} van tambien al archivo 'tags')"
        )
        print(f"Intervalo solicitado: {READ_TAGS_TIME_MS} ms")
        print("Servicio activo. Guardando cada cambio en disco...")

        await stop_event.wait()

        print("Deteniendo suscripcion OPC UA...")
        manejador.activo = False
        await suscripcion.delete()

    print("Servicio cerrado correctamente")
