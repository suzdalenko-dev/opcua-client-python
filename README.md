# Recogida de datos OPC UA (Pesadora ULMA / ANRITSU)

Recolector de datos de una **pesadora / control de calidad ULMA** (gateway CONTEC
CPS‑MCS341‑DS configurado por ANRITSU) mediante **OPC UA**. Guarda el dato crudo en
ficheros, consolida una línea por producción en **PostgreSQL** y expone KPIs de
**ritmo (kg/hora)** para un panel.

Proyecto **520746**.

---

## 1. Arquitectura (3 capas)

```
                                OPC UA SERVER
                         Pesadora / Gateway CONTEC
                                     │
                                     ▼
                            opcua_connection()
                              asyncua Client
                                     │
                              OPC UA subscription
                                     │
                                     ▼
                          SusctiptionHandler
                       datachange_notification()
                                     │
                              construye event
                                     │
                 ┌───────────────────┼──────────────────────┐
                 │                   │                      │
                 ▼                   ▼                      ▼
            EVENT_QUEUE          STATS_QUEUE             index_app()
          asyncio.Queue           queue.Queue                 │
                 │                   │                 actualiza ESTADO
                 │                   │                 valida coherencia
                 │                   │                      │
                 ▼                   ▼                      ▼
          jsonl_writer()       stats_writer thread        DB_QUEUE
           asyncio Task                                   queue.Queue
                 │                   │                      │
                 ▼                   ▼                      ▼
        asyncio.to_thread()     _append_stats()      database_writer
                 │                   │                    thread
                 ▼                   ▼                      │
         YYYY/MM-all.json     YYYY/MM-stats.json            ▼
                                                   get_database_connection()
                                                           │
                                                   persistent psycopg
                                                      connection
                                                           │
                                                           ▼
                                                      PostgreSQL
                                                           │
                                                           ▼
                                                   pesadora_lineas


                           ┌───────────────────────────────┐
                           │       HEARTBEAT THREAD        │
                           │                               │
                           │  CONNECTION_STATE             │
                           │  DB_QUEUE_PUSH                │
                           │  DB_INSERT_STATE              │
                           │           │                   │
                           │           ▼                   │
                           │  YYYY/MM-head-bit.json        │
                           └───────────────────────────────┘
```

Idea central: **recoger ≠ guardar ≠ mostrar**. Cada capa cambia por motivos
distintos y no se estorban.

---

## 2. Flujo de un dato

1. La pesadora publica un cambio de tag (`STAGxx`) por OPC UA.
2. `SusctiptionHandler.datachange_notification` (en `suscription_hadler_file.py`)
   construye un `event` y **solo encola** (trabajo mínimo, no bloquea).
3. Consumidores independientes escriben:
   - `EVENT_QUEUE` → `jsonl_writer` → `AAAA/MM-all.jsonl` (todos los tags).
   - `STATS_QUEUE` → `stats_writer` → `AAAA/MM-stats.json` (tags de estadística).
   - `index_app` (`app_recalculate_file.py`) acumula el estado y, cuando avanza el
     peso y los estadísticos son coherentes, encola en `DB_QUEUE`.
   - `DB_QUEUE` → `database_file` → `INSERT` en PostgreSQL (idempotente).
4. Un **heartbeat** en hilo aparte escribe periódicamente si el proceso sigue vivo
   y conectado.

---

## 3. Estructura del repositorio

```
main.py                         Arranque: suscripción OPC UA + lanzamiento de workers
config.py                       Configuración desde .env (falla rápido si falta algo)
requirements.txt
assets/
  suscription_hadler_file.py    Callback OPC UA -> encola eventos
  event_queue_file.py           EVENT_QUEUE (asyncio) · STATS_QUEUE, DB_QUEUE (queue)
  jsonl_writer.py               Consumidor async -> MM-all.jsonl
  stats_writer_file.py          Hilo -> MM-stats.json
  app_recalculate_file.py       Consolidación por producción -> DB_QUEUE
  database_file.py              Hilo -> INSERT PostgreSQL (conexión única + reconexión)
  hertbeat_writer_file.py       Hilo -> heartbeat (proceso vivo / conexión)
  conection_state_file.py       Estado de conexión (thread-safe)
  supervised_file.py            Relanza una corrutina si muere
  utils_file.py                 Fechas y parseo de valores
```

---

## 4. Tags STAG utilizados

Todos son `STRING`, solo lectura, patrón `ns=2;s=CPS-MCS341-DS.STAG.{tag}`.

**Estado / artículo en producción**
- `STAG00` operación (0=funciona, 1=parado, 2=ajuste, 3=check) · `STAG01` estado técnico
- `STAG02` producto seleccionado · `STAG21/22` producto y **nombre** de las estadísticas

**Pesada individual** (hasta 70/min; puede colapsar por el filtro de cambio de valor)
- `STAG10` nº secuencial · `STAG11` producto · `STAG12` clasificación (zona/OK-NG)
- `STAG13` rechazo (metal/externo/normal) · `STAG14` peso medido (g)

**Estadísticas acumuladas** (fiables; se reinician por lote)
- `STAG37` muestras buenas · `STAG38` peso total (kg) · `STAG39` peso medio (g)
- `STAG53` **conteo total de bolsas** · `STAG28–36` zonas y rechazos
- `STAG23/24` lote/batch · `STAG25/26` inicio/fin · `STAG27` método (0=todas / 1=solo PASS)

> **Recuento oficial** = estadísticas (`STAG53`, zonas), **no** el stream por pesada.

---

## 5. Requisitos e instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # asyncua, psycopg, python-dotenv
```

### `.env` (junto a `config.py`)

```dotenv
OPCUA_URL=opc.tcp://xxx:4840
OPCUA_NODE_ID_PREFIX=ns=2;s=CPS-MCS341-DS.STAG.
JSONL_BASE_DIRECTORY=/var/lib/suz-opcua
HEARTBEAT_FILE_NAME=head-bit.json
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=suz
POSTGRES_USER=suz
POSTGRES_PASSWORD=********
```

---

## 6. Base de datos

```sql
CREATE TABLE public.pesadora_lineas (
    id            bigserial PRIMARY KEY,
    art_erp       text,
    art_name      text,
    lote          text,
    batch         text,
    inicio_of     timestamp,
    fin_of        timestamp,
    bolsas_buenas integer,
    kg            numeric(12,3),
    peso_medio    numeric(10,2),
    bolsas_total  integer,
    "date"        timestamp
);

-- Idempotencia: evita duplicados aunque se reinicie o arranque dos veces
ALTER TABLE public.pesadora_lineas
    ADD CONSTRAINT pesadora_lineas_inicio_of_kg_unique UNIQUE (inicio_of, kg);
```

Cada línea se guarda cuando **avanza el peso acumulado** y los estadísticos son
coherentes (`kg·1000 / bolsas_buenas ≈ peso_medio`, tolerancia 0,1 g). Así solo se
persisten snapshots válidos.

---

## 7. Ejecución como servicio (systemd)

`/etc/systemd/system/suz-opcua.service`:

```ini
[Unit]
Description=suz OPC UA collector
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=suz
WorkingDirectory=/opt/suz-opcua
ExecStart=/opt/suz-opcua/.venv/bin/python /opt/suz-opcua/main.py
Environment=PYTHONUNBUFFERED=1
StateDirectory=suz-opcua
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now suz-opcua
sudo systemctl restart suz-opcua
journalctl -u suz-opcua -f
```

---

## 8. KPI de ritmo (API PHP)

Ritmo kg/hora en ventanas de 5 / 25 / 60 min: suma el incremento de `kg` del tramo
continuo del artículo actual y lo lleva a hora.

Notas importantes:
- Poner `date_default_timezone_set('Europe/Madrid')` (o anclar la ventana a
  `MAX(fin_of)`) porque `fin_of` es hora de la máquina y el servidor puede ir en UTC.
- Al reiniciarse el `kg` por lote, si `kg_actual < kg_anterior` = nuevo lote: no
  cruzar esa frontera al calcular.

---

## 9. Principios de diseño (pautas)

1. **No bloquear la recogida**: el callback OPC solo encola; la I/O va en workers.
2. **Colas + workers** (productor/consumidor): `asyncio.Queue` para consumidores
   async, `queue.Queue` para consumidores en hilo (¡no mezclar!).
3. **Todo se reconecta y se reinicia solo**; nada muere en silencio.
4. **Idempotencia**: clave única + `ON CONFLICT DO NOTHING`.
5. **Validar antes de persistir** (coherencia de los estadísticos).
6. **Guardar el crudo** (JSONL) y **derivar** lo procesado (PostgreSQL).
7. **Config por `.env`**; una sola zona horaria de referencia.
8. **Observabilidad**: heartbeat + logs en journald.

