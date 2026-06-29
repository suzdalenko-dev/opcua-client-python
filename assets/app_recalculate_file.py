'''
    Acumula el último valor de cada tag de producción y, al detectar el
    Nueva pesada sum de kg estadisticas, emite UNA línea consolidada para la base de datos.

'''

# Estado acumulado de la producción en curso.
# Se MUTA (ESTADO[k] = v) -> no necesita 'global'.
from assets.utils_file import current_date, value_to_number


ESTADO = {
    "art_erp": "",       # STAG21
    "art_name": "",      # STAG22 nombre del producto 
    "lote": "",          # STAG23
    "batch": "",         # STAG24
    "inicio_of": "",     # STAG25
    "fin_of": "",        # STAG26
    "bolsas_buenas": 0,  # STAG37
    "kg": 0.0,           # STAG38 peso total de las buenas
    "peso_medio": 0.0,   # STAG39
    "bolsas_total": 0,   # STAG53
}

# Tag OPC UA -> clave del estado
TAG_TO_KEY = {
    "STAG21": "art_erp",
    "STAG22": "art_name",
    "STAG23": "lote",
    "STAG24": "batch",
    "STAG25": "inicio_of",
    "STAG26": "fin_of",
    "STAG37": "bolsas_buenas",
    "STAG38": "kg",
    "STAG39": "peso_medio",
    "STAG53": "bolsas_total",
}

# Escalar que SÍ reasignamos -> este sí necesita 'global' dentro de la función.
old_peso_acumualado = None
 
def index_app(event):
    global TAG_TO_KEY
    global ESTADO
    global old_peso_acumualado

    tag = event["tag"]
    key = TAG_TO_KEY.get(tag)
    if key is None:  # tag que no nos interesa -> fuera rápido
        return 

    # 1. Actualizar el estado con el último valor de ese tag
    if key in ("bolsas_buenas", "bolsas_total", "kg", "peso_medio"):
        ESTADO[key] = value_to_number(event["value"])
    else:
        ESTADO[key] = event["value"]

    # 2. Detectar Cambio peso acumulado 
    if tag in ("STAG21", "STAG22", "STAG23", "STAG24", "STAG25", "STAG26", "STAG38", "STAG39", "STAG53"):
        peso_acumulado_actual = value_to_number(event["value"])

        if old_peso_acumualado  != peso_acumulado_actual:
            # mi idea es si cambia el valor de peso acumulado guardo la linea en la base datos 
            db_line_unique         = dict(ESTADO)
            db_line_unique['date'] = current_date()
            save_to_db(db_line_unique)

        old_peso_acumualado = peso_acumulado_actual


def save_to_db(db_line):
  # esta linea es la que guardare en la BD
  # para calcular ritmo kg/hora linea produccion utilizare varias lineas y
  # comprobando que las lineas buenas tienen valor de kg medio = kg acumulado total / numero bolsas buenas 
   print(db_line)