# Recolector de datos OPC UA — FROXA

Servicio en Python que se conecta por **OPC UA** a una pesadora con detector de
metales (equipo ULMA, gateway configurado por ANRITSU), se suscribe a sus
variables (`STAG…`) y va guardando cada cambio de valor en archivos JSON,
un archivo por mes.

El servicio está pensado para correr de forma permanente bajo **systemd**, que
lo reinicia automáticamente si se cae.

---

## Cómo se guardan los datos

Todo se guarda dentro de `LOG_DIRECTORY` (por defecto `/var/lib/froxa-opcua/`),
organizado por año:

```
/var/lib/froxa-opcua/
├── 2026/
│   ├── 06-all.jsonl     <- TODOS los tags de ese mes (junio)
│   └── 06-static.jsonl  <- solo los tags "de estadística" (los de TAGS)
├── health.json          <- estado del servicio en tiempo real
```

- **`MM-all.jsonl`**: una línea JSON por cada cambio de cualquier tag suscrito.
- **`MM-static.jsonl`**: las líneas de los tags definidos en `TAGS` (los de
  estadística) se guardan **además** aquí, para tenerlos por separado.

El valor se guarda **tal cual llega** del servidor: no se agrupa ni se
transforma por artículo, lote ni pesada.
- **`health.json`**: se reescribe continuamente con el estado del servicio
  (conectado, reconectando, espacio en disco, tamaño de la cola, etc.).

Cada línea tiene esta forma:

```json
{"received":"2026-06-27 10:00:00.123","timestamp":"2026-06-27 10:00:00.000","tag":"STAG21","value":"PRODUCTO_X"}
```

`received` es la hora a la que el servicio recibió el dato; `timestamp` es la
hora que reporta el propio servidor OPC UA.

---

## Cómo funciona por dentro (flujo)

1. **`main.py`** arranca el programa y prepara la parada ordenada (Ctrl+C / SIGTERM).
2. **`assets/service.py`** es el bucle principal: lanza el "escritor" de archivos
   y mantiene la conexión OPC UA; si se cae, espera y reconecta.
3. **`assets/connection.py`** abre la conexión con el cliente **asyncua**, se
   suscribe a todos los tags y vigila la conexión con un *watchdog*.
4. **`assets/suscription_handler.py`** recibe cada cambio de valor y lo mete en
   una cola en memoria.
5. **`assets/funcions/func.py`** contiene el escritor: saca eventos de la cola y
   los guarda en disco (con `fsync`, para que queden realmente escritos).
6. **`assets/funcions/func2.py`** = utilidades de fecha y de parada.
   **`assets/funcions/func3.py`** = escritura de `health.json` y disco.
7. **`config.py`** = toda la configuración (IP, tags, tiempos, límites).

La cola tiene un tamaño máximo. Si se llenara (por ejemplo, si el disco dejara
de escribir), el servicio se detiene a propósito para no agotar la RAM, y
systemd lo reinicia.

---

## Puesta en marcha

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py            # arranque manual para probar
```

Para producción, instala la unidad systemd (ver instrucciones dentro de
`froxa-opcua.service`).

---

## Configuración (`config.py`)

Los parámetros más importantes:

- `URL` — dirección del servidor OPC UA (`opc.tcp://192.168.14.30:4840`).
- `TAGS` — tags de estadística (se guardan también en `MM-stat.json`).
- `OTHER_TAGS` — el resto de tags (solo en `MM-all.json`).
- `READ_TAGS_TIME_MS` — cada cuánto pide cambios al servidor.
- `RECONNECT_DELAY_SECONDS` — espera entre reintentos de conexión.
- `WATCHDOG_INTERVAL_SECONDS` — cada cuánto comprueba que OPC UA responde.
- `WATCHDOG_READ_TIMEOUT_SECONDS` — cuánto espera esa comprobación antes de
  dar la conexión por caída.
- `EVENT_QUEUE_MAX_SIZE` — máximo de eventos en memoria.
- `MIN_FREE_DISK_BYTES` — mínimo de disco libre antes de parar (1 GB).

---

## Correcciones aplicadas

El proyecto no arrancaba. Se corrigieron estos puntos:

1. **Import circular** entre `func.py` y `func3.py` (se importaban mutuamente).
   Se movieron `get_free_disk_bytes` y `get_health_file_path` a `func3.py`, de
   forma que las dependencias van en un solo sentido.
2. **Cliente equivocado** en `connection.py`: importaba `Client` de
   `multiprocessing` en lugar del cliente OPC UA. Ahora usa `from asyncua import Client`.
3. **`ALL_TAGS`** se importaba desde `main` (donde no existe). Ahora se importa
   desde `config`.
4. **`stop_writer_normally`** se importaba desde `func` (no estaba ahí). Ahora se
   importa desde `func2`, que es donde está definida.
5. Imports duplicados eliminados y **timeout** añadido a la lectura del watchdog
   para que una conexión "colgada" no bloquee el servicio.
