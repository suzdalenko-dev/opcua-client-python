from pathlib import Path


# ----------------------------------------------------------------------
# CONFIGURACION
# Este es el UNICO sitio donde se definen los tags y los parametros.
# main.py los importa de aqui (no los redefine).
# ----------------------------------------------------------------------

# --- Conexion OPC UA ---
URL = "opc.tcp://192.168.14.30:4840"
NODE_ID_PREFIX = "ns=2;s=CPS-MCS341-DS.STAG."
READ_TAGS_TIME_MS = 222
MONITORED_ITEM_QUEUE_SIZE = 1000

# --- Donde se guardan los datos ---
LOG_DIRECTORY = Path("/var/lib/froxa-opcua")


# Estos van al SEGUNDO archivo (ademas del de "todas").
TAGS = [
    "STAG21",  # producto de las estadisticas
    "STAG22",  # nombre del producto
    "STAG23",  # nº de lote

    "STAG37",  # muestras buenas (excluye dobles/fuera objetivo)
    "STAG38",  # peso total kg (producto bueno)
    "STAG39",  # peso medio
]

# El resto de tags (solo van al archivo "todas").
OTHER_TAGS = [
    "STAG00",  # Estado operativo (0=funciona,1=parado,2=ajuste,3=check)
    "STAG01",  # Estado tecnico actual del equipo
    "STAG02",  # Receta/producto seleccionado
    "STAG10",  # Secuencia de pesada 0..9  -> dispara una bolsa
    "STAG11",  # Producto de la pesada
    "STAG12",  # Clasificacion del peso (zona / OK / NG)
    "STAG13",  # Rechazo metal (0) / externo (1) / normal (' ')
    "STAG14",  # Peso medido

    "STAG24",  # nº de batch  -> detecta cierre de lote
    "STAG27",  # metodo: 0=todas / 1=solo PASS  (define que cuenta STAG37)
    "STAG53",  # conteo TOTAL de bolsas

    "STAG28",  # -NG / Zona A  (peso bajo)
    "STAG29",  # OK / Zona B
    "STAG30",  # Zona C
    "STAG31",  # Zona D
    "STAG32",  # +NG / Zona E  (peso alto)
    "STAG33",  # rechazos metal
    "STAG34",  # rechazos externos
    "STAG35",  # dobles producto
    "STAG36",  # fuera del objetivo estadistico
    "STAG25",  # inicio del lote
    "STAG26",  # fin del lote
]


# Todos los tags a los que nos suscribimos (van al archivo "todas").
ALL_TAGS = tuple(dict.fromkeys(TAGS + OTHER_TAGS))

# Conjunto para comprobar rapido si un tag va tambien al segundo archivo.
STAT_TAGS = frozenset(TAGS)
