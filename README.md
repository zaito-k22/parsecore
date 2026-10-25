# Parsecore

API para recibir facturas en PDF o imagen, extraer su texto con OCR,
estructurarlo con un LLM local (Ollama) y devolver un JSON trazable.

Stack: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, PaddleOCR y
Ollama. La gestión de dependencias y del entorno se hace con `uv`.

## Requisitos

- Python 3.12 (gestionado por `uv` o instalado en el sistema).
- `uv`.
- PostgreSQL para las rutas que persisten facturas.
- Ollama y PaddleOCR solo para procesar documentos reales o ejecutar pruebas de
  integración.

## Preparación

```bash
uv sync --dev
```

Las pruebas unitarias no necesitan PostgreSQL, Ollama ni PaddleOCR y se
ejecutan por defecto:

```bash
uv run pytest -q
uv run ruff check .
```

Las pruebas de base de datos están marcadas `db` y las de OCR/Ollama,
`integration`. Ambas se excluyen por defecto.

## Configuración

Copia `.env.example` a `.env` y ajusta los valores en tu entorno local. No
subas `.env`, claves, tokens ni facturas reales al repositorio.

Variables principales:

- `DATABASE_URL`
- `OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`
- `LOG_LEVEL`

## PostgreSQL para pruebas

`compose.test.yml` define un PostgreSQL 17 aislado para pruebas:

- Contenedor: `parsecore-test-db`.
- Base de datos y usuario: `parsecore_test`.
- Escucha solo en `127.0.0.1:55432`.
- Datos en el volumen nombrado `parsecore_test_pgdata`.
- La contraseña se toma obligatoriamente de `TEST_DB_PASSWORD`.

Usa `postgres:17` y está pensado únicamente para desarrollo y pruebas. No lo
uses en producción. Tampoco inyecta ni sustituye `DATABASE_URL` en la
aplicación.

### Crear `.env.test`

El archivo real `.env.test` está ignorado por Git. Créalo a partir del ejemplo
y genera una contraseña local aleatoria sin mostrarla en la terminal:

```bash
umask 077
cp compose.test.env.example .env.test
sed -i "s|^TEST_DB_PASSWORD=.*|TEST_DB_PASSWORD=$(openssl rand -hex 32)|" .env.test
chmod 600 .env.test
```

No ejecutes estos comandos con `set -x` ni reutilices contraseñas de otros
servicios. El archivo de ejemplo contiene un valor ficticio y no debe usarse
tal cual.

### Iniciar y comprobar

```bash
docker compose --env-file .env.test -f compose.test.yml up -d
docker compose --env-file .env.test -f compose.test.yml ps
docker compose --env-file .env.test -f compose.test.yml exec test-db \
  pg_isready -U parsecore_test -d parsecore_test
```

Si `pg_isready` está instalado en el host, también puedes comprobar el puerto
publicado:

```bash
pg_isready -h 127.0.0.1 -p 55432 -U parsecore_test -d parsecore_test
```

### Detener

Para detener el servicio sin borrar los datos:

```bash
docker compose --env-file .env.test -f compose.test.yml down
```

El volumen `parsecore_test_pgdata` se conserva. `docker compose down -v`
elimina el volumen y, por tanto, todos los datos de pruebas.

### Pruebas automatizadas

La URL exclusiva de pruebas es:

```text
postgresql+psycopg://parsecore_test:<TEST_DB_PASSWORD>@127.0.0.1:55432/parsecore_test
```

El fixture `test_database_url` de `tests/conftest.py` construye esa URL
leyendo `TEST_DB_PASSWORD` de `.env.test`. No hace falta exportar la contraseña
ni incorporar la URL a Git. También se puede inyectar `TEST_DATABASE_URL` en el
entorno del proceso; la guarda la valida igualmente.

La guarda de `app/db/testing.py` exige el driver `postgresql+psycopg`, el
usuario `parsecore_test`, el host `127.0.0.1`, el puerto `55432`, la base
`parsecore_test`, una contraseña no vacía y ninguna opción de conexión en la
query string. Si la URL no coincide, no se crea el engine.
`app/db/migrations/env.py` aplica la misma guarda cuando existe
`TEST_DATABASE_URL`, para que una migración de prueba no pueda apuntar a otra
base.

Validar la configuración sin conectar a PostgreSQL:

```bash
uv run python -m app.db.testing
```

Ejecutar solo las pruebas unitarias:

```bash
uv run pytest -q
# Equivalente explícito:
uv run pytest -m "not db and not integration" -q
```

Ejecutar las pruebas que requieren PostgreSQL:

```bash
uv run pytest -m db -q
```

La prueba de integración actual solo ejecuta `SELECT 1` y consulta
`current_database()` y `current_user`; no modifica el esquema ni inserta datos
de negocio. No crea tablas ni esquemas temporales, así que no requiere limpieza.
Si en el futuro se añaden objetos temporales, deberán eliminarse en un
`finally` o en el teardown de un fixture aunque la prueba falle.

No guardes `TEST_DATABASE_URL` con contraseña ni `.env.test` en archivos
versionados.

## Estructura

- `app/api/`: rutas HTTP.
- `app/models/`, `app/schemas/`, `app/repositories/`: persistencia y contrato.
- `app/services/`: OCR, LLM, normalización y orquestación.
- `app/db/`: sesión, guardas de pruebas y migraciones de Alembic.
- `tests/`: pruebas unitarias y de integración; `tests/samples/` contiene
  documentos de ejemplo.

## Calidad

Ruff está configurado para Python 3.12 con las reglas `E`, `F`, `I`, `B` y `UP`
sobre el proyecto. Pytest usa `tests/` como directorio de
pruebas, declara los marcadores `db` e `integration` y los excluye por defecto.

```bash
uv run ruff check .
uv run pytest -q
```
