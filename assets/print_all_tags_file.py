import json
from pathlib import Path
from asyncua import ua


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_NODES_FILE = (
    PROJECT_ROOT
    / "opcua-nodes.jsonl"
)


async def descubrir_nodos(
    node,
    archivo_path=None,
    profundidad_maxima=20,
):
    """
    Recorre el árbol OPC UA y guarda la información descriptiva
    de todos los nodos en un archivo JSONL.

    Si no se proporciona archivo_path, se guarda en:
    <raíz del proyecto>/opcua-nodes.jsonl

    No lee los valores de las variables.
    Devuelve el número total de nodos encontrados.
    """

    if archivo_path is None:
        archivo_path = DEFAULT_NODES_FILE
    else:
        archivo_path = Path(archivo_path)

    archivo_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    visitados = set()
    numero_nodos = 0

    def convertir_a_json(value):
        if value is None:
            return None

        if isinstance(
            value,
            (str, int, float, bool),
        ):
            return value

        if isinstance(value, (list, tuple)):
            return [
                convertir_a_json(element)
                for element in value
            ]

        if hasattr(value, "to_string"):
            try:
                return value.to_string()
            except Exception:
                pass

        if hasattr(value, "Text"):
            return value.Text

        if hasattr(value, "Name"):
            return {
                "namespace_index": getattr(
                    value,
                    "NamespaceIndex",
                    None,
                ),
                "name": value.Name,
            }

        if hasattr(value, "name"):
            return value.name

        return str(value)

    async def recorrer(
        current_node,
        nivel,
        ruta_padre,
        parent_node_id,
        file,
    ):
        nonlocal numero_nodos

        node_id = current_node.nodeid.to_string()

        if node_id in visitados:
            return

        visitados.add(node_id)
        numero_nodos += 1

        async def leer_atributo(attribute_id):
            try:
                data_value = (
                    await current_node.read_attribute(
                        attribute_id
                    )
                )

                if data_value is None:
                    return None

                if data_value.Value is None:
                    return None

                return data_value.Value.Value

            except Exception:
                return None

        browse_name = await leer_atributo(
            ua.AttributeIds.BrowseName
        )

        display_name = await leer_atributo(
            ua.AttributeIds.DisplayName
        )

        description = await leer_atributo(
            ua.AttributeIds.Description
        )

        node_class = await leer_atributo(
            ua.AttributeIds.NodeClass
        )

        write_mask = await leer_atributo(
            ua.AttributeIds.WriteMask
        )

        user_write_mask = await leer_atributo(
            ua.AttributeIds.UserWriteMask
        )

        try:
            node_class_name = ua.NodeClass(
                node_class
            ).name
        except Exception:
            node_class_name = str(node_class)

        browse_name_text = ""

        if browse_name is not None:
            namespace_index = getattr(
                browse_name,
                "NamespaceIndex",
                None,
            )

            name = getattr(
                browse_name,
                "Name",
                None,
            )

            if name is not None:
                browse_name_text = (
                    f"{namespace_index}:{name}"
                )
            else:
                browse_name_text = str(
                    browse_name
                )

        if ruta_padre:
            ruta = (
                f"{ruta_padre}/"
                f"{browse_name_text or node_id}"
            )
        else:
            ruta = browse_name_text or node_id

        record = {
            "node_id": node_id,
            "parent_node_id": parent_node_id,
            "nivel": nivel,
            "ruta": ruta,
            "browse_name": browse_name_text,
            "display_name": convertir_a_json(
                display_name
            ),
            "description": convertir_a_json(
                description
            ),
            "node_class": node_class_name,
            "write_mask": convertir_a_json(
                write_mask
            ),
            "user_write_mask": convertir_a_json(
                user_write_mask
            ),
        }

        if node_class == ua.NodeClass.Variable:
            record.update(
                {
                    "data_type": convertir_a_json(
                        await leer_atributo(
                            ua.AttributeIds.DataType
                        )
                    ),
                    "value_rank": convertir_a_json(
                        await leer_atributo(
                            ua.AttributeIds.ValueRank
                        )
                    ),
                    "array_dimensions":
                        convertir_a_json(
                            await leer_atributo(
                                ua.AttributeIds
                                .ArrayDimensions
                            )
                        ),
                    "access_level": convertir_a_json(
                        await leer_atributo(
                            ua.AttributeIds.AccessLevel
                        )
                    ),
                    "user_access_level":
                        convertir_a_json(
                            await leer_atributo(
                                ua.AttributeIds
                                .UserAccessLevel
                            )
                        ),
                    "minimum_sampling_interval":
                        convertir_a_json(
                            await leer_atributo(
                                ua.AttributeIds
                                .MinimumSamplingInterval
                            )
                        ),
                    "historizing": convertir_a_json(
                        await leer_atributo(
                            ua.AttributeIds.Historizing
                        )
                    ),
                }
            )

        if node_class == ua.NodeClass.Method:
            record.update(
                {
                    "executable": convertir_a_json(
                        await leer_atributo(
                            ua.AttributeIds.Executable
                        )
                    ),
                    "user_executable":
                        convertir_a_json(
                            await leer_atributo(
                                ua.AttributeIds
                                .UserExecutable
                            )
                        ),
                }
            )

        hijos = []

        if nivel < profundidad_maxima:
            try:
                hijos = (
                    await current_node.get_children()
                )
            except Exception as error:
                record["children_error"] = repr(
                    error
                )

        record["children_count"] = len(hijos)

        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        )

        for hijo in hijos:
            await recorrer(
                current_node=hijo,
                nivel=nivel + 1,
                ruta_padre=ruta,
                parent_node_id=node_id,
                file=file,
            )

    with archivo_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        await recorrer(
            current_node=node,
            nivel=0,
            ruta_padre="",
            parent_node_id=None,
            file=file,
        )

    return numero_nodos