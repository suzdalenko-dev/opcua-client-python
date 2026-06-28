import asyncio

from assets.event_queue_file import EVENT_QUEUE
from assets.utils_file import current_date, format_datetime
from config import TAGS


class SusctiptionHandler:
    def __init__(self, tag_by_node_id,):
        self.tag_by_node_id = tag_by_node_id
        self.active         = True

    def datachange_notification(self, node, value, data,):
        if not self.active:
            return
        
        print(data)
        
        # -------------------------------------------------
        # 1. Identificar el nodo y el tag
        # -------------------------------------------------

        node_id = node.nodeid.to_string()
        tag = self.tag_by_node_id.get(node_id, node_id,)

        
        # -------------------------------------------------
        # 2. Extraer DataValue y Variant desde data
        # -------------------------------------------------

        monitored_item = data.monitored_item
        data_value = monitored_item.Value
        variant = data_value.Value

        # Valor original exacto enviado por la máquina.
        raw_value = variant.Value

        # Valor limpio, quitando espacios laterales.
        clean_value = (
            raw_value.strip()
            if isinstance(raw_value, str)
            else raw_value
        )

        # -------------------------------------------------
        # 3. Estado OPC UA
        # -------------------------------------------------

        status_code_object = data_value.StatusCode
        status_code = status_code_object.value
        status_good = status_code_object.is_good()

        # -------------------------------------------------
        # 4. Fechas OPC UA
        # -------------------------------------------------

        source_timestamp = data_value.SourceTimestamp
        server_timestamp = data_value.ServerTimestamp


        # 5. Escribir los TAGS de estadisticas

        if tag in TAGS:
            # con un Tread nuevo y con toda la seguridad/simplicidad/estabilidad 
            print("aqui quiero guradar cada TAG que lleva en un archivo stats")



        # -------------------------------------------------
        # 6. Construir el diccionario archivo all
        # -------------------------------------------------

        event = {
            "date": current_date(),
            "tag": tag,
            "value_raw": raw_value,
            "value": clean_value,
            "code": status_code,
            "good": status_good,
            "source_t": format_datetime(source_timestamp),
            "server_t": format_datetime(server_timestamp),
        }

        print(event)

        # -------------------------------------------------
        # 7. Introducirlo en la cola global archivo all
        # -------------------------------------------------

        try:
            EVENT_QUEUE.put_nowait(event,)

        except Exception as e:
            print(f"ERROR SUSCRIPTION HANDLER {e}")
            print(str(e))

