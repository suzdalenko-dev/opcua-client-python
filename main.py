"""
Punto de entrada del recolector OPC UA de FROXA.

Responsabilidad UNICA de este modulo: arrancar el servicio y pararlo
de forma ordenada cuando llega Ctrl+C (SIGINT) o systemd (SIGTERM).

Estructura del proyecto:
    config.py          -> configuracion (URL, tags, rutas)
    almacenamiento.py  -> guarda los datos en disco (jsonl + fsync)
    suscripcion.py     -> recibe los cambios del equipo
    servicio.py        -> conecta y mantiene la suscripcion
    main.py            -> arranca todo (este archivo)
"""

import asyncio
import signal

from servicio import ejecutar


def configurar_senales_de_parada(stop_event):
    loop = asyncio.get_running_loop()

    def manejar_parada(signum, frame):
        print("Senal de parada recibida...")
        loop.call_soon_threadsafe(stop_event.set)

    signal.signal(signal.SIGINT, manejar_parada)
    signal.signal(signal.SIGTERM, manejar_parada)


async def main():
    stop_event = asyncio.Event()
    configurar_senales_de_parada(stop_event)

    await ejecutar(stop_event)


if __name__ == "__main__":
    asyncio.run(main())
