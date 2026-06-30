import threading
import time
import psycopg

from assets.event_queue_file import DB_QUEUE
from config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)


DATABASE_RETRY_SECONDS = 5


# Solo lo utiliza el hilo database-writer.
_connection = None

# Referencia al hilo para impedir arrancarlo dos veces.
_writer_thread = None

# Protege únicamente el arranque del hilo.
_start_lock = threading.Lock()


def create_database_connection():
    """
    Crea una conexión PostgreSQL nueva.

    autocommit=True confirma cada INSERT
    individualmente.
    """
    connection = psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=5,
        autocommit=True,
        application_name="suzdalenko-opcua",
    )

    print(
        "PostgreSQL conectado: "
        f"{POSTGRES_USER}@"
        f"{POSTGRES_HOST}:"
        f"{POSTGRES_PORT}/"
        f"{POSTGRES_DB}",
        flush=True,
    )

    return connection


def close_database_connection():
    """
    Cierra y elimina la conexión actual.
    """
    global _connection

    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass

    _connection = None


def get_database_connection():
    """
    Devuelve siempre la misma conexión.

    Si todavía no existe o se cerró, crea otra.
    """
    global _connection

    if (
        _connection is None
        or _connection.closed
    ):
        _connection = create_database_connection()

    return _connection


def insert_pesadora_line(db_line):
    """
    Inserta una línea en public.pesadora_lineas.

    Devuelve:
        id   si se insertó.
        None si ya existía inicio_of + kg.
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
            bolsas_total,
            peso_medio,
            date
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
        ON CONFLICT ON CONSTRAINT
            pesadora_lineas_inicio_of_kg_unique
        DO NOTHING
        RETURNING id
    """

    values = (
        str(db_line["art_erp"]),
        str(db_line["art_name"]),
        str(db_line["lote"]),
        str(db_line["batch"]),
        str(db_line["inicio_of"]),
        str(db_line["fin_of"]),
        float(db_line["bolsas_buenas"]),
        float(db_line["kg"]),
        float(db_line["bolsas_total"]),
        float(db_line["peso_medio"]),
        str(db_line["date"]),
    )

    connection = get_database_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            sql,
            values,
        )

        row = cursor.fetchone()

    # ON CONFLICT DO NOTHING no devuelve ninguna fila.
    if row is None:
        return None

    return row[0]


def database_writer_loop():
    """
    Consume permanentemente DB_QUEUE.

    Si PostgreSQL falla, mantiene la línea actual
    y vuelve a intentar guardarla.
    """
    while True:
        db_line = DB_QUEUE.get()

        try:
            while True:
                try:
                    inserted_id = insert_pesadora_line(
                        db_line
                    )

                    if inserted_id is None:
                        print(
                            "Línea PostgreSQL duplicada: "
                            f"inicio_of="
                            f"{db_line['inicio_of']}, "
                            f"kg={db_line['kg']}",
                            flush=True,
                        )

                    else:
                        print(
                            "Línea PostgreSQL guardada: "
                            f"id={inserted_id}, "
                            f"inicio_of="
                            f"{db_line['inicio_of']}, "
                            f"kg={db_line['kg']}, "
                            f"bolsas="
                            f"{db_line['bolsas_buenas']}",
                            flush=True,
                        )

                    # La línea ya fue insertada o era duplicada.
                    break

                except Exception as error:
                    close_database_connection()

                    print(
                        "ERROR PostgreSQL. "
                        "Se volverá a intentar la misma "
                        f"línea en "
                        f"{DATABASE_RETRY_SECONDS} segundos: "
                        f"{error!r}",
                        flush=True,
                    )

                    time.sleep(
                        DATABASE_RETRY_SECONDS
                    )

        finally:
            DB_QUEUE.task_done()


def start_database_writer():
    """
    Arranca el hilo PostgreSQL una sola vez.
    """
    global _writer_thread

    with _start_lock:
        if (
            _writer_thread is not None
            and _writer_thread.is_alive()
        ):
            return _writer_thread

        _writer_thread = threading.Thread(
            target=database_writer_loop,
            name="database-writer",
            daemon=True,
        )

        _writer_thread.start()

        return _writer_thread