"""
Manejador de la suscripcion OPC UA.

Responsabilidad UNICA de este modulo: recibir cada cambio de valor que
envia el equipo, extraer los datos utiles y pasarlos a 'almacenamiento'.
No sabe nada de conexiones ni de archivos.
"""

from datetime import datetime

from almacenamiento import guardar


class ManejadorSuscripcion:
    def __init__(self, tag_por_node_id):
        self.tag_por_node_id = tag_por_node_id
        self.activo = True

    def datachange_notification(self, node, value, data):
        if not self.activo:
            return

        # Un fallo puntual en un dato NO debe detener el servicio:
        # se registra el error por consola y se sigue.
        try:
            node_id = node.nodeid.to_string()
            tag = self.tag_por_node_id.get(node_id)

            if tag is None:
                return

            data_value = data.monitored_item.Value
            variant = data_value.Value

            variant_type = "" if variant is None else str(variant.VariantType)

            guardar(
                tag=tag,
                value=value,
                node_id=node_id,
                source_timestamp=data_value.SourceTimestamp,
                server_timestamp=data_value.ServerTimestamp,
                status_code=str(data_value.StatusCode),
                variant_type=variant_type,
            )

        except Exception as error:
            print(
                f"{datetime.now().astimezone():%Y-%m-%d %H:%M:%S} "
                f"[ERROR al guardar un dato] {error!r}"
            )
