"""
Diagnostico del recolector OPC UA de FROXA.

Ejecutar en el servidor, desde la carpeta del proyecto y con el venv activo:

    source .venv/bin/activate
    python diagnostico.py

Comprueba, por orden:
  1) Si se puede ESCRIBIR en LOG_DIRECTORY  (causa habitual del "se apaga al arrancar").
  2) Si CONECTA con el servidor OPC UA.
  3) Si puede LEER el valor actual de cada tag (lectura directa = snapshot).
  4) Si la SUSCRIPCION entrega cambios durante 30 s (aqui se ve si el gateway empuja datos).

Al final imprime un RESUMEN con el veredicto.
No modifica ni borra nada (solo crea y elimina un archivo de prueba).
"""

import asyncio
from pathlib import Path

from asyncua import Client

from config import ALL_TAGS, LOG_DIRECTORY, NODE_ID_PREFIX, READ_TAGS_TIME_MS, URL


def probar_escritura_en_disco():
    print(f"[1] Probando escritura en LOG_DIRECTORY = {LOG_DIRECTORY}")
    try:
        directorio = Path(LOG_DIRECTORY)
        directorio.mkdir(parents=True, exist_ok=True)
        prueba = directorio / ".prueba_escritura.tmp"
        prueba.write_text("ok", encoding="utf-8")
        prueba.unlink()
        print("    OK: se puede crear la carpeta y escribir en ella.\n")
        return True
    except Exception as error:
        print(f"    ERROR: no se puede escribir -> {error!r}")
        print("    => Esta es, casi seguro, la causa de que el servicio se apague al arrancar.")
        print("       Solucion: crear la carpeta con el dueño correcto, p.ej.:")
        print("         sudo mkdir -p", LOG_DIRECTORY)
        print("         sudo chown $USER", LOG_DIRECTORY)
        print("       (o usar la unidad systemd, que lo hace con StateDirectory).\n")
        return False


class HandlerDiagnostico:
    def __init__(self):
        self.total = 0

    def datachange_notification(self, node, valor, datos):
        self.total += 1
        print(f"    NOTIFICACION #{self.total}: {node.nodeid.to_string()} = {valor!r}")


async def main():
    disco_ok = probar_escritura_en_disco()

    leidos = 0
    handler = HandlerDiagnostico()

    print(f"[2] Conectando con {URL} ...")
    try:
        async with Client(url=URL, timeout=10) as client:
            print("    OK: conexion establecida.\n")

            nodos = {tag: client.get_node(f"{NODE_ID_PREFIX}{tag}") for tag in ALL_TAGS}

            print(f"[3] Lectura directa del valor actual de los {len(nodos)} tags:")
            for tag, nodo in nodos.items():
                try:
                    dv = await nodo.read_data_value()
                    leidos += 1
                    print(f"    {tag} = {dv.Value.Value!r}   (status={dv.StatusCode})")
                except Exception as error:
                    print(f"    {tag} -> ERROR de lectura: {error!r}")
            print(f"    => {leidos}/{len(nodos)} tags leidos correctamente.\n")

            print("[4] Probando la SUSCRIPCION durante 30 s")
            print("    (si el gateway empuja cambios, apareceran NOTIFICACION abajo):")
            subscripcion = await client.create_subscription(READ_TAGS_TIME_MS, handler)
            await subscripcion.subscribe_data_change(
                list(nodos.values()),
                queuesize=1000,
                sampling_interval=READ_TAGS_TIME_MS,
            )
            await asyncio.sleep(30)
            print(f"\n    => Notificaciones recibidas en 30 s: {handler.total}")
            await subscripcion.delete()

    except Exception as error:
        print(f"    ERROR de conexion/suscripcion: {error!r}\n")

    print("\n===================== RESUMEN =====================")
    print(f" Escritura en disco .......... {'OK' if disco_ok else 'FALLA (causa del apagado al arrancar)'}")
    print(f" Lectura directa de tags ..... {leidos}/{len(ALL_TAGS)}")
    print(f" Cambios por suscripcion (30s) {handler.total}")
    print("---------------------------------------------------")
    if leidos > 0 and handler.total == 0:
        print(" VEREDICTO: el gateway DEJA LEER pero NO entrega cambios por suscripcion.")
        print("            -> Hay que cambiar a LECTURA PERIODICA (polling).")
    elif handler.total > 0:
        print(" VEREDICTO: la suscripcion SI funciona. El problema esta en otra parte")
        print("            (probablemente permisos de escritura en LOG_DIRECTORY).")
    elif leidos == 0:
        print(" VEREDICTO: no se pudo leer ningun tag. Revisar URL, NODE_ID_PREFIX o el equipo.")
    print("===================================================")


if __name__ == "__main__":
    asyncio.run(main())
