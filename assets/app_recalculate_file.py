'''
    Aqui preparo los datos acumulados para guardarlos en la base datos  
    La idea es que a partir de aqui se calcule el ritmo kg/hora
'''

INICIO_OF_STATS = ''
FIN_OF_STATS    = ''

def index_app(event):
    print(event)

    if event['tag'] == 'STAG25':
        INICIO_OF = event['value']
    elif event['tag'] == 'STAG26':
        FIN_OF_STATS = event['value']


    line_db = {
        'date':      event['date'],
        'inicio_of': INICIO_OF,
        'fin_of':    FIN_OF_STATS,
        'art_name': '',
        'art_erp': '',
        'lote': '',
        'batch': '',
        'kg': 0
    }  

    print(line_db)



def save_to_db():
   # gurdar linea en la base datos 