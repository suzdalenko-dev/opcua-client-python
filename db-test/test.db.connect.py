import os
from pathlib import Path
import psycopg
from dotenv import load_dotenv
load_dotenv(dotenv_path='../.env',)

BASE_DIRECTORY = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIRECTORY / ".env"

load_dotenv(dotenv_path=ENV_FILE)

def test_database_connection():
    try:
        with psycopg.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=int(os.getenv("POSTGRES_PORT")),
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASS"),
            connect_timeout=5,
        ) as connection:

            with connection.cursor() as cursor:

                # ----------------------------------------
                # 1. Comprobar usuario y base de datos
                # ----------------------------------------

                cursor.execute(
                    """
                    SELECT
                        current_user,
                        current_database(),
                        inet_server_addr(),
                        inet_server_port()
                    """
                )

                (
                    current_user,
                    current_database,
                    server_address,
                    server_port,
                ) = cursor.fetchone()

                print("CONEXIÓN POSTGRESQL CORRECTA")
                print(f"Usuario: {current_user}")
                print(f"Base de datos: {current_database}")
                print(f"Servidor: {server_address}")
                print(f"Puerto: {server_port}")

                # ----------------------------------------
                # 2. Comprobar que existe la tabla
                # ----------------------------------------

                cursor.execute(
                    """
                    SELECT to_regclass(
                        'public.pesadora_lineas'
                    )
                    """
                )

                table_name = cursor.fetchone()[0]

                if table_name is None:
                    print(
                        "ERROR: no existe la tabla "
                        "public.pesadora_lineas"
                    )
                else:
                    print(
                        f"Tabla encontrada: {table_name}"
                    )

                    # ------------------------------------
                    # 3. Comprobar permisos reales
                    # ------------------------------------

                    cursor.execute(
                        """
                        SELECT
                            has_table_privilege(
                                current_user,
                                'public.pesadora_lineas',
                                'SELECT'
                            ),
                            has_table_privilege(
                                current_user,
                                'public.pesadora_lineas',
                                'INSERT'
                            ),
                            has_table_privilege(
                                current_user,
                                'public.pesadora_lineas',
                                'UPDATE'
                            ),
                            has_table_privilege(
                                current_user,
                                'public.pesadora_lineas',
                                'DELETE'
                            )
                        """
                    )

                    (
                        can_select,
                        can_insert,
                        can_update,
                        can_delete,
                    ) = cursor.fetchone()

                    print("Permisos pesadora_lineas:")
                    print(f"  SELECT: {can_select}")
                    print(f"  INSERT: {can_insert}")
                    print(f"  UPDATE: {can_update}")
                    print(f"  DELETE: {can_delete}")

                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM public.pesadora_lineas
                        """
                    )

                    number_of_rows = cursor.fetchone()[0]

                    print(
                        f"Filas actuales: {number_of_rows}"
                    )

                # ----------------------------------------
                # 4. Prueba CRUD sin tocar la tabla real
                # ----------------------------------------

                cursor.execute(
                    """
                    CREATE TEMPORARY TABLE opcua_db_test (
                        id BIGINT
                            GENERATED ALWAYS AS IDENTITY
                            PRIMARY KEY,

                        texto TEXT NOT NULL
                    )
                    """
                )

                cursor.execute(
                    """
                    INSERT INTO opcua_db_test (texto)
                    VALUES (%s)
                    RETURNING id
                    """,
                    ("prueba de conexión OPC UA",),
                )

                test_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    UPDATE opcua_db_test
                    SET texto = %s
                    WHERE id = %s
                    """,
                    (
                        "prueba modificada correctamente",
                        test_id,
                    ),
                )

                cursor.execute(
                    """
                    SELECT texto
                    FROM opcua_db_test
                    WHERE id = %s
                    """,
                    (test_id,),
                )

                test_text = cursor.fetchone()[0]

                cursor.execute(
                    """
                    DELETE FROM opcua_db_test
                    WHERE id = %s
                    """,
                    (test_id,),
                )

                print("PRUEBA DE ESCRITURA CORRECTA")
                print(f"Texto leído: {test_text}")
                print("INSERT: correcto")
                print("SELECT: correcto")
                print("UPDATE: correcto")
                print("DELETE: correcto")

    except psycopg.OperationalError as error:
        print("ERROR DE CONEXIÓN POSTGRESQL")
        print(error)

    except psycopg.Error as error:
        print("ERROR DE POSTGRESQL")
        print(error)

    except Exception as error:
        print("ERROR GENERAL")
        print(repr(error))


if __name__ == "__main__":
    test_database_connection()



'''
usuario@svr-prod:/opt/froxa-opcua/opcua$ /opt/froxa-opcua/.venv/bin/python /opt/froxa-opcua/opcua/db-test/test.db.connect.py
python-dotenv could not parse statement starting at line 25
CONEXIÓN POSTGRESQL CORRECTA
Usuario: opcua
Base de datos: opcua_prod
Servidor: 127.0.0.1
Puerto: 5432
Tabla encontrada: pesadora_lineas
Permisos pesadora_lineas:
  SELECT: True
  INSERT: True
  UPDATE: True
  DELETE: True
Filas actuales: 0
PRUEBA DE ESCRITURA CORRECTA
Texto leído: prueba modificada correctamente
INSERT: correcto
SELECT: correcto
UPDATE: correcto
DELETE: correcto
usuario@svr-prod:/opt/froxa-opcua/opcua$ 

'''