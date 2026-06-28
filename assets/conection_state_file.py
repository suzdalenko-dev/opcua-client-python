import threading


class ConnectionState:
    '''Mantiene de forma segura el estado de la conexion actual OPC UA'''
    def __init__(self,):
        self._state_connection = False
        self._lock = threading.Lock()

    def set_connected(self, connected):
        with self._lock:
            self._state_connection = bool(connected,)

    def is_connected(self):
        with self._lock:
            return self._state_connection
        


# Una única instancia compartida por todo el programa.
CONNECTION_STATE = ConnectionState()