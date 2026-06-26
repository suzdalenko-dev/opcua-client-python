URL                       = "opc.tcp://192.168.14.30:4840"
READ_TAGS_TIME_MS         = 222
MONITORED_ITEM_QUEUE_SIZE = 1000
NODE_ID_PREFIX            = "ns=2;s=CPS-MCS341-DS.STAG."
LOG_DIRECTORY             = "/var/lib/froxa-opcua/"

# Datos por pesada (rápidos, llegan en cada bolsa con la cinta en marcha)
TAGS = [
    "STAG21",  # producto de las estadísticas
    "STAG22",  # nombre del producto
    "STAG23",  # nº de lote

    "STAG37",  # muestras buenas (excluye dobles/fuera objetivo)
    "STAG38",  # peso total kg (producto bueno)
    "STAG39",  # peso medio
]

# Estadísticas acumuladas (se refrescan ~cada 2 s, se resetean por lote).
# Son la fuente EXACTA para reconstruir la verdad de lo que pasó.
OTHER_TAGS = [
    "STAG00",  # Estado operativo (0=funciona,1=parado,2=ajuste,3=check)
    "STAG01",  # Estado técnico actual del equipo  
    "STAG02",  # Receta/producto seleccionado
    "STAG10",  # Secuencia de pesada 0..9  -> dispara una bolsa
    "STAG11",  # Producto de la pesada
    "STAG12",  # Clasificación del peso (zona / OK / NG)
    "STAG13",  # Rechazo metal (0) / externo (1) / normal (' ')
    "STAG14",  # Peso medido


    "STAG24",  # nº de batch  -> detecta cierre de lote
    "STAG27",  # método: 0=todas / 1=solo PASS  (define qué cuenta STAG37)
    "STAG53",  # conteo TOTAL de bolsas (todas las que manejó el sistema)

    "STAG28",  # -NG / Zona A  (peso bajo)
    "STAG29",  # OK / Zona B
    "STAG30",  # Zona C
    "STAG31",  # Zona D
    "STAG32",  # +NG / Zona E  (peso alto)
    "STAG33",  # rechazos metal  (VERIFICAR que cuenta)
    "STAG34",  # rechazos externos
    "STAG35",  # dobles producto
    "STAG36",  # fuera del objetivo estadístico
    "STAG25",  # inicio del lote
    "STAG26",  # fin del lote
]

# Tiempo entre intentos de reconexión.
RECONNECT_DELAY_SECONDS = 22


# Cada cuánto se comprueba que OPC UA responde.
WATCHDOG_INTERVAL_SECONDS = 222


# Reintentos de escritura antes de considerar
# que existe un fallo grave de almacenamiento.
DISK_WRITE_MAX_RETRIES = 3
DISK_RETRY_SECONDS = 5


# Máximo de eventos pendientes en memoria.
#
# Si la cola se llena, el proceso termina con error
# para evitar consumir toda la memoria RAM.
EVENT_QUEUE_MAX_SIZE = 10000


# Tiempo máximo para guardar los eventos
# pendientes durante una parada normal.
QUEUE_DRAIN_TIMEOUT_SECONDS = 60


# El servicio se detiene si queda menos
# de 1 GB libre en la partición.
MIN_FREE_DISK_BYTES = (
    1
    * 1024
    * 1024
    * 1024
)


# En producción debe permanecer en False
# para no llenar journald.
PRINT_EACH_EVENT = False

# Lista única de todos los tags suscritos.
ALL_TAGS = tuple(
    dict.fromkeys(TAGS + OTHER_TAGS)
)

# Tags que se escriben también en el archivo de estadísticas.
STAT_TAGS = frozenset(TAGS)


'''
Regla robusta para tu código (sin inventar): considera "reset / lote nuevo" cuando ocurra cualquiera de estas dos:

STAG24  # nº de batch  -> detecta cierre de lote | sirve tambien para inicio/fin de las estadisticas ?¿???¿? o para que me sirve
STAG25  # inicio del lote
STAG26  # fin del lote

STAG37 <- numero count pesadas buenas
STAG38 <- kg pesadas buenas tramo
STAG39 <- media AVERAGE(KG) del tramos
STAG53 <- numero cout total pesadas

Respondiendo a tu pregunta directa:
STAG24 → te dice en qué nº de batch va la máquina. NO sirve para inicio/fin ni como disparador de reset. No lo uses para resetear.



STAG25 = inicio de la producción/serie. Su valor es la fecha real de arranque. ✓
STAG26 = fin "hasta ahora". Pero ojo, no crece siempre: crece mientras produce y se congela en los paros (lo probamos: se quedó clavado en 11:57:40 durante 17 min). Su último valor antes del cierre = el fin real de esa producción. ✓
Ambos a 0000-00-00 00:00:00 = borrado → sin producción activa (limbo entre producciones). ✓
'''