import threading

import psycopg

from config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)


# Única conexión PostgreSQL utilizada por el proceso.
_connection = None

# Evita que dos llamadas utilicen o reconstruyan
# simultáneamente la misma conexión.
_connection_lock = threading.RLock()


def create_database_connection():
    """
    Crea una nueva conexión PostgreSQL.

    autocommit=True hace que cada INSERT quede confirmado
    inmediatamente, sin tener que ejecutar commit().
    """
    connection = psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=5,
        autocommit=True,
        application_name="froxa-opcua",
    )

    print(
        f"PostgreSQL conectado: "
        f"{POSTGRES_USER}@{POSTGRES_HOST}:{POSTGRES_PORT}/"
        f"{POSTGRES_DB}"
    )

    return connection


def close_database_connection():
    """
    Cierra y elimina la conexión actual.
    """
    global _connection

    with _connection_lock:
        if _connection is not None:
            try:
                _connection.close()
            except Exception:
                pass

        _connection = None


def get_database_connection():
    """
    Devuelve la conexión existente.

    Si todavía no existe o está cerrada, crea una nueva.
    """
    global _connection

    with _connection_lock:
        if _connection is None or _connection.closed:
            _connection = create_database_connection()

        return _connection


def insert_pesadora_line(db_line):
    """
    Inserta una línea en public.pesadora_lineas.

    Si la conexión se pierde, la reconstruye y vuelve
    a intentar el INSERT una sola vez.
    """
    sql = """
        INSERT INTO public.pesadora_lineas (
            art_erp,
            art_name,
            lote,
            batch,
            inicio_of,
            fin_of,
            bolsas_buenas,
            kg,
            peso_medio,
            bolsas_total,
            "date"
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        RETURNING id
    """

    values = (
        db_line["art_erp"],
        db_line["art_name"],
        db_line["lote"],
        db_line["batch"],
        db_line["inicio_of"],
        db_line["fin_of"],
        db_line["bolsas_buenas"],
        db_line["kg"],
        db_line["peso_medio"],
        db_line["bolsas_total"],
        db_line["date"],
    )

    with _connection_lock:
        for attempt in range(1, 3):
            connection = get_database_connection()

            try:
                with connection.cursor() as cursor:
                    cursor.execute(sql, values)

                    inserted_id = cursor.fetchone()[0]

                return inserted_id

            except (
                psycopg.OperationalError,
                psycopg.InterfaceError,
            ):
                close_database_connection()

                if attempt == 2:
                    raise