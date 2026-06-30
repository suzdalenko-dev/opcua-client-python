import asyncio
from asyncua import Client
from assets.conection_state_file import CONNECTION_STATE
from assets.database_file import start_database_writer
from assets.hertbeat_writer_file import write_headbeat_log
from assets.jsonl_writer import jsonl_writer
from assets.stats_writer_file import start_stats_writer
from assets.supervised_file import supervised
from assets.suscription_hadler_file import SusctiptionHandler
from config import ALL_TAGS, NODE_ID_PREFIX, READ_TAGS_TIME_MS, URL


async def opcua_connection():
    #  stop_event = asyncio.Event()

    async with Client(url=URL, timeout=22, watchdog_intervall=222.1,) as conn:
        print(conn)

        # Crear un objeto node para cada tag 
        nodes_by_tag = {
            tag: conn.get_node(f"{NODE_ID_PREFIX}{tag}")
            for tag in ALL_TAGS
        } 

        # Relacion inversa -> NodeId completo -> nombre STAG
        tag_by_node_id = {
            node.nodeid.to_string(): tag
            for tag, node in nodes_by_tag.items()
        }


        # Crear suscripcion OPC UA
        handler      = SusctiptionHandler(tag_by_node_id=tag_by_node_id,)
        subscription = await conn.create_subscription(READ_TAGS_TIME_MS, handler) 
        await subscription.subscribe_data_change(list(nodes_by_tag.values()), queuesize=1000, sampling_interval=READ_TAGS_TIME_MS)


        while True: 
            await conn.check_connection()
            CONNECTION_STATE.set_connected(True)
            print('Conectado')
            await asyncio.sleep(22)
            



async def main():
    write_headbeat_log()                                # escritura de head bit 
    #  writer_task = asyncio.create_task(jsonl_writer())   # consumidor de la cola todos los STAGS
    writer_task = asyncio.create_task(supervised(jsonl_writer, "json_writer"))
    start_stats_writer()
    start_database_writer()

    while True:
        try:
            CONNECTION_STATE.set_connected(False)
            await opcua_connection()
        except Exception as e:
            print(f"ERROR MAIN {e}")
            await asyncio.sleep(11)
        finally:
            CONNECTION_STATE.set_connected(False)



if __name__ == '__main__':
    asyncio.run(main())


