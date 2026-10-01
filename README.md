# ToneFlowers

Customer flower shop website and FastAPI backend for Cairo and Giza. The website is
Arabic-first, supports English, and reads products from the API. Orders are priced
and validated by the backend. There is no payment or customer account system yet.

## Start the backend (Windows Command Prompt)

```bat
cd /d "C:\Users\mohamed harbe\flower-shop"
if not exist .venv py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
python -m alembic upgrade head
python -m uvicorn backend.main:app --reload
```

Keep the ignored `.env` file private. Set `ADMIN_API_KEY` to a long random value
before using admin routes. Set `SMTP_USERNAME` and `SMTP_PASSWORD` to a Gmail
account and its App Password to enable owner notifications. The local `.env`
already has the two requested notification recipients; verify them before use.
Swagger UI is at <http://127.0.0.1:8000/docs>.

The database migration command is required before starting a fresh checkout.
Alembic first adopts the original schema, then adds catalog and governorate
columns, then adds order notification and idempotency tracking. It does not
delete old products or orders. Historical orders have a null governorate or
idempotency key when those values were not recorded, and keep their original
free-text delivery slots. New orders require Cairo or Giza and a fixed slot.
SQLite remains the development default. Set `DATABASE_URL` to a
`postgresql+psycopg://...` URL when preparing a PostgreSQL deployment.

## Local PostgreSQL on Windows

Both SQLite and PostgreSQL are supported. `Settings` reads the ignored `.env`;
a `DATABASE_URL` environment variable overrides it for that terminal/process.

| Use | Connection URL example |
| --- | --- |
| Local SQLite | `sqlite:///./flower_shop.db` |
| Local PostgreSQL | `postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/toneflowers` |
| PostgreSQL tests | `postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/toneflowers_test` |

Keep existing `flower_shop.dp` files and their `.env` configuration if you have
already used the original SQLite setup. Changing the filename selects another
database; it does not transfer existing data. PostgreSQL setup does not import
SQLite data automatically.

Create the development and test databases separately on your local PostgreSQL
server. Do not use the shop database for automated tests. Passwords must be URL
encoded when included in a connection URL; do not commit real credentials.

This workstation's verified local installation uses PostgreSQL **18.6** from the
[EDB Windows binaries](https://www.enterprisedb.com/download-postgresql-binaries),
under `%LOCALAPPDATA%\ToneFlowers\PostgreSQL18`. It listens only on localhost,
port 5432, with SCRAM authentication. It is a local process, not a Windows
service, so start it after a reboot. Its generated password is stored in
`postgres.credential.xml` encrypted with Windows DPAPI for the current Windows
user, outside the repository. The existing `.env` was not overwritten.

PowerShell, from the project directory:

```powershell
$pgRoot = Join-Path $env:LOCALAPPDATA 'ToneFlowers\PostgreSQL18'
& "$pgRoot\pgsql\bin\pg_ctl.exe" -D "$pgRoot\data" status
# If the server is stopped:
& "$pgRoot\pgsql\bin\pg_ctl.exe" -D "$pgRoot\data" -l "$pgRoot\server.log" -o '-h localhost -p 5432' -w start

$pgCredential = Import-Clixml "$pgRoot\postgres.credential.xml"
$pgPassword = [Uri]::EscapeDataString($pgCredential.GetNetworkCredential().Password)
$env:DATABASE_URL = "postgresql+psycopg://postgres:${pgPassword}@localhost:5432/toneflowers"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Use the existing website commands below in a second terminal. Stop a running
backend before replacing it; an occupied port 8000 can leave an older server
serving a stale schema. Confirm the running `/docs` request schema after a restart.

To return to the `.env` database, stop FastAPI and run
`Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue` before restarting.
To select a new SQLite file explicitly, set
`$env:DATABASE_URL = 'sqlite:///./flower_shop.db'` and apply migrations first.

## Start the website (second Command Prompt)

```bat
cd /d "C:\Users\mohamed harbe\flower-shop\frontend"
if not exist .env copy .env.example .env
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. Build the production files with `npm run build`.
The build checks TypeScript before writing `frontend/dist/`.

## Configuration

Backend `.env` values are shown in [.env.example](.env.example):

- `DATABASE_URL`: SQLite locally, PostgreSQL URL for production.
- `CORS_ORIGINS`: comma-separated explicit frontend origins. Set production
  origins to the deployed site URL; wildcard origins are rejected.
- `ADMIN_API_KEY`: required for product writes, order status updates, and
  sensitive order lookup. Send it in `X-Admin-Key`. Replace this temporary gate
  with real admin accounts before production.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`: Gmail SMTP. The
  password must be an App Password, never a normal account password.
- `SHOP_NOTIFICATION_EMAILS`: comma-separated owner recipients. The example
  contains `toneflowerss@gmail.com,midoharpi02@gmail.com`.

Frontend `.env` values are shown in [frontend/.env.example](frontend/.env.example):

- `VITE_API_URL`: backend URL, for example `http://127.0.0.1:8000` locally.
- `VITE_WHATSAPP_URL`, `VITE_PHONE`, `VITE_EMAIL`, `VITE_INSTAGRAM_URL`: optional
  contact channels. Unconfigured channels are hidden.
- `VITE_FACEBOOK_URL`: the ToneFlowers Facebook page supplied for this project.

Do not put private keys or SMTP credentials in `VITE_` variables: frontend
variables are visible in the browser.

## API and order flow

- `GET /products` lists active products; `GET /products/{id}` gets one.
- `POST /products` and `PATCH /products/{id}` require `X-Admin-Key`.
- `POST /orders` is public. Send customer, receiver, delivery, and gift details
  with item `product_id` and `quantity`. Send `governorate` as `Cairo` or `Giza`,
  `delivery_slot` as `morning`, `afternoon`, or `evening`, and a UUID
  `idempotency_key`. Repeating the same key returns the saved order without
  reducing stock or sending another notification. Do not send price, total,
  status, or server-generated IDs.
- `GET /orders` (optional `status` and `delivery_date` filters),
  `GET /orders/{id}`, and `PATCH /orders/{id}/status` require `X-Admin-Key`.

At checkout, the website refreshes product availability and sends IDs and
quantities. FastAPI validates the order; SQLAlchemy calculates prices, stores
items, and reduces stock in one transaction. After commit, a background task
sends the owner email. A mail failure is logged and cannot undo the order.
The email task uses its own database session and sets `notified_at` only after
all configured recipients are accepted by SMTP. A null value means successful
notification has not been recorded; background tasks do not retry automatically.
The success page uses the `POST /orders` response, so it does not fetch private
order details through a sequential public ID.

Both customer and receiver mobile numbers are normalized to `+201xxxxxxxx`;
the optional email address is validated. An order can move from pending to
confirmed or cancelled, confirmed to preparing or cancelled, preparing to
out_for_delivery or cancelled, and out_for_delivery to delivered. Delivered
and cancelled orders are final. Cancellation returns all item quantities to
stock in the same transaction as the status change, exactly once.

Business dates use `Africa/Cairo` (including Egypt's daylight saving rules).
New timestamps are timezone-aware in Python and returned as Cairo times.
SQLite stores UTC as a naive DATETIME because its native DATETIME does not
retain offsets; the application reattaches UTC and converts to Cairo on read.
PostgreSQL uses TIMESTAMP WITH TIME ZONE. The migration interprets old naive
`created_at` values as Cairo wall time before converting them to UTC.

The cart stores only product IDs and quantities in localStorage. Product data
and displayed prices are refreshed from FastAPI. Filters and sorting currently
run in the browser over `GET /products` results; there is no simulated catalog
or hard-coded product price fallback.

## Tests

```bat
cd /d "C:\Users\mohamed harbe\flower-shop"
.venv\Scripts\activate.bat
python -m unittest discover -s tests -v
cd frontend
npm ci
npm run build
```

The default suite uses temporary SQLite databases. To run **all database tests
on PostgreSQL**, explicitly set `TEST_DATABASE_URL` in PowerShell. Merely setting
`DATABASE_URL` does not opt tests into PostgreSQL. Test credentials are not read
from `.env`, and the test runner never uses the development URL as its target.

```powershell
$pgRoot = Join-Path $env:LOCALAPPDATA 'ToneFlowers\PostgreSQL18'
$pgCredential = Import-Clixml "$pgRoot\postgres.credential.xml"
$pgPassword = [Uri]::EscapeDataString($pgCredential.GetNetworkCredential().Password)
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:${pgPassword}@localhost:5432/toneflowers_test"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# Explicit PostgreSQL HTTP concurrency run:
.\.venv\Scripts\python.exe -m unittest tests.test_postgres_concurrency -v
# Return to the SQLite test suite:
Remove-Item Env:TEST_DATABASE_URL
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
```

PostgreSQL tests accept only a `postgresql+psycopg` URL for the local database
named `toneflowers_test`, without URL query options. Each test creates a unique
`tf_test_...` schema and removes only that schema afterwards. The test role must
be able to create schemas in that test database. Public tables are not truncated
or dropped. Migration tests run the entire migration history in empty schemas
and compare types, nullability, defaults, indexes and foreign keys with the models.
They also verify that the catalog-default migration preserves existing rows.

The PostgreSQL concurrency tests use independent connections at `READ COMMITTED`
and real local HTTP requests. They force overlapping attempts for the last stock
unit, reversed product lists (12 pairs), cancellation, and shared idempotency
keys. They also cover a replay whose initial lookup precedes the winner's commit,
then observes exhausted stock, and a second-item failure after the first stock
decrement. All automated notifications are mocked. The seven PostgreSQL-specific
tests are explicitly skipped when `TEST_DATABASE_URL` is absent.

PostgreSQL stores `created_at` and `notified_at` as `TIMESTAMP WITH TIME ZONE`.
SQLite stores naive UTC values; `CairoDateTime` restores timezone information and
returns `Africa/Cairo` in both cases. Both use Decimal values for `NUMERIC(10, 2)`.
Migration `20261001_04` removes the catalog flags' old backfill defaults so the
database matches the ORM; it preserves the flags' existing values and the ORM's
Python defaults. `alembic check` includes server-default comparison.

## Before launch

- Replace the existing development catalog entries with real names, Arabic
  names, descriptions, prices, stock, and usable `https://` image URLs. Add
  category, occasion, featured, and best-seller values to enable browsing
  sections; the site does not invent this merchandise data.
- Supply Gmail credentials and verify real delivery to both recipients.
- Replace the temporary admin API key with proper administrator authentication.
- Use a dependable job queue or outbox when guaranteed email retries are
  needed; in-process background tasks can be lost if the server stops.
- Configure the production site origin and HTTPS deployment. Back up the
  database before future migrations.

The authentic ToneFlowers logo is sourced from the shop's public Facebook
profile. The homepage floral photograph is an original generated site asset.
