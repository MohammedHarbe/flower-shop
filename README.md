The frontend sets localized page titles and descriptions, uses the existing
ToneFlowers logo as its favicon, and marks `/admin` as `noindex, nofollow`.
`frontend/public/robots.txt` disallows crawling `/admin`, but robots directives
are not an access-control mechanism. No canonical URL or production domain is
configured until the actual domain is selected.
# ToneFlowers

Customer flower shop website and FastAPI backend for Cairo and Giza. The website is
Arabic-first, supports English, and reads products from the API. Orders are priced
and validated by the backend. Customers can choose Vodafone Cash (manual review)
or Cash on Delivery; there is no online card gateway or customer account system.

## Start the backend (Windows Command Prompt)

```bat
cd /d "C:\Users\mohamed harbe\flower-shop"
if not exist .venv py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
python -m alembic upgrade head
python -m backend.seed_catalog
python -m uvicorn backend.main:app --reload
```

`backend.seed_catalog` is the business bootstrap: it idempotently activates Cairo
and Giza at 50.00 EGP. It never creates demo products. To intentionally load or
remove the development/staging demo catalog, run `python -m
backend.seed_demo_catalog` or `python -m backend.remove_demo_catalog` separately.
Start the frontend in another terminal with `cd frontend`, `npm ci`, and
`npm run dev`.

Keep the ignored `.env` file private. For local browser admin, set
`ADMIN_LOGIN_EMAIL`, a `ADMIN_PASSWORD_HASH` generated with
`backend.admin_auth.hash_password`, and a random `ADMIN_SESSION_SECRET` of at
least 32 characters. Keep `ADMIN_API_KEY` for trusted maintenance tools. Set
`SMTP_USERNAME` and `SMTP_PASSWORD` to a Gmail account and its App Password to
enable owner notifications. The local `.env` already has private business and
notification values; do not copy them into examples or commit them.
Swagger UI is at <http://127.0.0.1:8000/docs>.

The database migration command is required before starting a fresh checkout.
The business bootstrap command idempotently activates Cairo and Giza delivery
zones at 50.00 EGP. Demo products are created only by the separate explicit
development/staging command, never automatically at startup or in production.
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
For local cookie-based admin login, keep the frontend URL hostname aligned
with `VITE_API_URL` (for example, use `127.0.0.1` for both).

## Configuration

Backend `.env` values are shown in [.env.example](.env.example):

- `DATABASE_URL`: SQLite locally, PostgreSQL URL for production.
- `APP_ENV`: `development` locally; set `staging` or `production` when deployed.
  Startup checks require PostgreSQL, a strong maintenance key, hashed browser-admin
  credentials, a session secret, HTTPS origins and mail configuration in those
  environments. Configured secrets shorter than 32 characters are rejected.
- `CORS_ORIGINS`: comma-separated explicit frontend origins. Set production
  origins to the deployed site URL; wildcard origins are rejected.
- `ADMIN_API_KEY`: maintenance access for product writes, order status updates,
  delivery-zone changes, and sensitive order lookup. Send it in `X-Admin-Key`
  only from a trusted operator tool over HTTPS; never embed it in the frontend.
- `ADMIN_LOGIN_EMAIL`, `ADMIN_PASSWORD_HASH`, `ADMIN_SESSION_SECRET`:
  browser-admin credentials. The dashboard at `/admin` uses a signed HttpOnly
  session cookie; the password is stored only as the supported PBKDF2-SHA256
  hash. Cookie-authenticated writes require an allowed `Origin` and the
  `X-Requested-With: ToneFlowersAdmin` header. Production cookies are Secure.
  Keep the login email, password hash, session secret, and maintenance key in
  the ignored local `.env` or deployment secret store only.
- `ADMIN_SESSION_TTL_SECONDS`, `ADMIN_LOGIN_RATE_LIMIT_PER_MINUTE`,
  `ORDER_RATE_LIMIT_PER_MINUTE`: session lifetime and per-process throttles.
- `MEDIA_DIR`, `MEDIA_BASE_URL`, `MEDIA_PERSISTENT_STORAGE`: product image
  storage. Development uploads use local disk; production uploads are disabled
  unless `MEDIA_PERSISTENT_STORAGE=true` explicitly declares that `MEDIA_DIR` is
  a durable mounted disk. A local container filesystem is not durable. URL-based
  images continue to work when uploads are disabled.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`: Gmail SMTP. The
  password must be an App Password, never a normal account password.
- `SHOP_NOTIFICATION_EMAILS`: comma-separated owner recipients. Public examples
  use placeholders; the two real recipients stay in the ignored backend `.env`
  or the deployment secret store.

Frontend `.env` values are shown in [frontend/.env.example](frontend/.env.example):

- `VITE_API_URL`: backend URL, for example `http://127.0.0.1:8000` locally.
- `VITE_SITE_URL`: optional real frontend origin. When set, public pages receive
  canonical URLs; when unset, no canonical URL is emitted.
- `VITE_WHATSAPP_URL`, `VITE_PHONE`, `VITE_EMAIL`, `VITE_INSTAGRAM_URL`: optional
  contact channels. Unconfigured channels are hidden.
- `VITE_FACEBOOK_URL`: the ToneFlowers Facebook page supplied for this project.

Do not put private keys or SMTP credentials in `VITE_` variables: frontend
variables are visible in the browser.

## API and order flow

- `GET /products` lists active products; `GET /products/{id}` gets one.
- `GET /health` is public: `200 {"status":"ok"}` after a read-only `SELECT 1`;
  a database failure returns `503 {"status":"unavailable"}` without error details.
  It checks connectivity, not migrations, SMTP delivery or the product catalog.
- Admin browser routes use the session cookie: `/admin/login`, `/admin/logout`,
  and `/admin/me`. The `/admin` dashboard manages products, orders, payment
  review, and delivery fees. Trusted scripts may use `X-Admin-Key` instead.
- `GET /delivery-zones` is public and lists active backend-priced zones.
  `GET /admin/products`, product writes, `/delivery-zones/admin`, delivery-zone
  writes, order details, status changes, and payment-status changes are admin-only.
- `POST /orders` is public. Send customer, receiver, delivery, and gift details
  with item `product_id` and `quantity`. Send `governorate` as `Cairo` or `Giza`,
  `delivery_slot` as `morning`, `afternoon`, or `evening`, and a UUID
  `idempotency_key`. Repeating the same key returns the saved order without
  sending another notification. Numeric stock is legacy data only: orders do not
  decrement or restore it and are never rejected based on it. Only `active` controls
  whether a product can be ordered. Do not send price, total,
  status, or server-generated IDs.
- The public `POST /orders` response contains only the order ID, status, delivery
  area/date/slot, payment method/status, and backend-calculated totals. It omits
  customer/receiver contact information, full address, gift message, notes,
  coordinates, and idempotency key. Full order details require admin auth.
- `GET /orders` (optional `status` and `delivery_date` filters),
  `GET /orders/{id}`, and `PATCH /orders/{id}/status` require `X-Admin-Key`.

At checkout, the website refreshes product activity and sends IDs and
quantities. FastAPI validates active products; SQLAlchemy calculates prices and
stores items in one transaction without reading or changing numeric stock. New
orders start pending until ToneFlowers confirms availability. Vodafone Cash
instructions are shown only after that confirmation. After commit, a background task
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
and cancelled orders are final. Cancellation changes order status only; it does
not mutate legacy product stock.

Business dates use `Africa/Cairo` (including Egypt's daylight saving rules).
New timestamps are timezone-aware in Python and returned as Cairo times.
SQLite stores UTC as a naive DATETIME because its native DATETIME does not
retain offsets; the application reattaches UTC and converts to Cairo on read.
PostgreSQL uses TIMESTAMP WITH TIME ZONE. The migration interprets old naive
`created_at` values as Cairo wall time before converting them to UTC.

The cart stores only product IDs and quantities in localStorage. Product data
and displayed prices are refreshed from FastAPI. Filters and sorting currently
run in the browser over `GET /products` results; there is no simulated catalog
or hard-coded product price fallback. The Bassiony help panel uses a fixed,
bilingual FAQ and a public WhatsApp handoff; it makes no AI/API calls.

### Demo catalog and image sources

Run `python -m backend.seed_demo_catalog` only in development or staging. It
upserts eight bilingual products with names marked `DEMO -`, sample prices,
descriptions, and varied featured/best-seller flags. It refuses production.
Run `python -m backend.remove_demo_catalog` to delete only known seed-owned demo
records; cleanup aborts if a demo product is referenced by an order. Demo image
URLs remain empty because no source/license could be confidently verified, so
the storefront placeholder is used. See
[frontend/public/images/SOURCES.md](frontend/public/images/SOURCES.md).

**REPLACE DEMO PRODUCTS AND DEMO PRICES WITH REAL TONEFLOWERS DATA BEFORE PUBLIC LAUNCH.**

### Product image uploads

Admins can upload JPEG, PNG, or WebP images up to 5 MB, or continue using an
external HTTP(S) image URL. Uploads are decoded and re-encoded, named randomly,
and served from the configured media URL. SVG, GIF, mismatched content, and
unknown formats are rejected. Development stores files under `media/products/`.
Production uploads remain disabled unless a persistent disk is mounted at
`MEDIA_DIR` and `MEDIA_PERSISTENT_STORAGE=true` is set. Configure backups and
serve the durable disk at `MEDIA_BASE_URL`; the default container filesystem is
not durable. No cloud storage vendor is integrated. Use external image URLs if
durable production storage has not been configured.

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
and real local HTTP requests. They cover overlapping orders with zero legacy
stock, reversed item lists, cancellation, and shared idempotency keys. They also
cover replay after the winner commits and inactive-product rejection. All
automated notifications are mocked. The seven PostgreSQL-specific
tests are explicitly skipped when `TEST_DATABASE_URL` is absent.

PostgreSQL stores `created_at` and `notified_at` as `TIMESTAMP WITH TIME ZONE`.
SQLite stores naive UTC values; `CairoDateTime` restores timezone information and
returns `Africa/Cairo` in both cases. Both use Decimal values for `NUMERIC(10, 2)`.
Migration `20261001_04` removes the catalog flags' old backfill defaults so the
database matches the ORM; it preserves the flags' existing values and the ORM's
Python defaults. `alembic check` includes server-default comparison.

## Staging and production deployment runbook

Preparation only: no hosting provider, production database or domain has been
selected or created by this work. Keep staging separate from production, with
its own database, credentials and clearly marked test orders. The SQL and shell
commands below are operator instructions, not automatic startup scripts.

### Architecture and HTTPS

```text
Customer browser -> React static frontend
                         | HTTPS API requests
                         v
                    FastAPI API -> PostgreSQL
                         |
                         +-> Gmail SMTP (STARTTLS)
```

Serve both frontend and API through HTTPS at the hosting platform or a reverse
proxy. Customer phone numbers and addresses, and the private `X-Admin-Key`
header, must be encrypted in transit. No customer login/session system is
introduced. Redirect public HTTP to HTTPS at the edge. Keep PostgreSQL private
or allow connections only from the API/deployment service; use the provider's
verified TLS connection settings for remote database traffic. Do not expose
the raw Uvicorn listener publicly without the HTTPS edge. Trust forwarded
headers only from your platform's documented proxy addresses.

### Backend environment and secrets

Set these in the platform's secret/environment settings, not source control:

```dotenv
APP_ENV=production
DATABASE_URL=postgresql+psycopg://toneflowers_app:URL_ENCODED_PASSWORD@DB_HOST:5432/toneflowers
CORS_ORIGINS=https://toneflowers.example
ADMIN_API_KEY=REPLACE_WITH_A_GENERATED_RANDOM_KEY
ADMIN_LOGIN_EMAIL=admin@example.com
ADMIN_PASSWORD_HASH=pbkdf2_sha256$REPLACE_WITH_32_HEX_SALT$REPLACE_WITH_64_HEX_DIGEST
ADMIN_SESSION_SECRET=REPLACE_WITH_A_GENERATED_RANDOM_SECRET
WHATSAPP_NUMBER=PUBLIC_SHOP_WHATSAPP_NUMBER
VODAFONE_CASH_NUMBER=PUBLIC_VODAFONE_CASH_NUMBER
MEDIA_DIR=/var/lib/toneflowers/media
MEDIA_BASE_URL=/media
MEDIA_PERSISTENT_STORAGE=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sender@example.com
SMTP_PASSWORD=REPLACE_WITH_GMAIL_APP_PASSWORD
SHOP_NOTIFICATION_EMAILS=owner-one@example.com,owner-two@example.com
```

Use `APP_ENV=staging` for staging; it applies the same checks. These are
placeholders, not deployable credentials. Generate the admin key locally with
`python -c "import secrets; print(secrets.token_urlsafe(32))"` and store the result
privately. Generate a password hash interactively without placing the password
in shell history:

```powershell
python -c "import getpass; from backend.admin_auth import hash_password; print(hash_password(getpass.getpass('Admin password: ')))"
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Store the resulting hash and session secret in the platform secret store. Length
validation is a minimum, not an entropy check. Rotate the maintenance key and
session secret when access changes. Never pass credentials in a URL or include
them in `VITE_` values. Keep admin access restricted to HTTPS and a trusted
operator. The session cookie is HttpOnly, Secure in staging/production, and
protected against cross-site writes by exact-Origin validation and a custom
request header. The process-local login/order rate limiter is appropriate only
for the documented single-worker deployment; it is not shared across workers.

Environment variables override the ignored backend `.env`. `.env.*` files are
also ignored, except `.env.example`. Existing Git history is not rewritten:
removing private examples from today's files does not erase earlier commits.
If a credential has ever been shared or committed, replace it before launch.

URL-encode the username/password components, **not the whole database URL**.
For example, password `example@pass:/?#%` becomes
`example%40pass%3A%2F%3F%23%25`. When assembling a URL in Python, use
`urllib.parse.quote(password, safe="")` or SQLAlchemy `URL.create()` rather
than concatenating an unescaped password. Use the remote `DB_HOST`, not localhost.
Keep provider TLS parameters, for example `?sslmode=verify-full` with the trusted
CA configured as required by that provider. Never print a completed secret URL.

Production CORS must name browser origins exactly, without paths, query strings,
credentials or wildcards. Multiple sites use a comma-separated value:

```dotenv
CORS_ORIGINS=https://toneflowers.example,https://www.toneflowers.example
```

Development defaults allow only `http://localhost:5173` and
`http://127.0.0.1:5173`. Staging/production startup rejects HTTP origins and empty
origin lists. CORS controls browser access; it does not replace the admin key.

### Restricted PostgreSQL roles

Have the operator provision a dedicated database named `toneflowers` first.
The following commands assume that database has been explicitly identified;
do not run them on a shared or unknown database. In `psql`, connected as its
authorized database administrator, create two non-superuser roles. Use
`\password` so passwords are prompted rather than written in SQL history:

```sql
CREATE ROLE toneflowers_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
CREATE ROLE toneflowers_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
```

```text
\password toneflowers_migrator
\password toneflowers_app
\connect toneflowers
```

Configure privileges in that dedicated database:

```sql
REVOKE ALL ON DATABASE toneflowers FROM PUBLIC;
GRANT CONNECT ON DATABASE toneflowers TO toneflowers_migrator, toneflowers_app;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO toneflowers_migrator;
GRANT USAGE ON SCHEMA public TO toneflowers_app;
ALTER ROLE toneflowers_app IN DATABASE toneflowers SET search_path = public;
ALTER ROLE toneflowers_migrator IN DATABASE toneflowers SET search_path = public;

ALTER DEFAULT PRIVILEGES FOR ROLE toneflowers_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO toneflowers_app;
ALTER DEFAULT PRIVILEGES FOR ROLE toneflowers_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO toneflowers_app;
```

Run `python -m alembic upgrade head` using the **migrator** URL in that deployment
step. New tables will be owned by `toneflowers_migrator`. Then, as the migrator
or administrator, apply grants for existing tables and protect migration metadata:

```sql
GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE public.products, public.orders, public.order_items TO toneflowers_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO toneflowers_app;
REVOKE ALL ON TABLE public.alembic_version FROM toneflowers_app;
```

Reapply the metadata revoke after migrations that recreate `alembic_version`.
If adopting tables created previously by `postgres`, transfer just these owned
objects as an administrator before the next migration:

```sql
ALTER TABLE public.products OWNER TO toneflowers_migrator;
ALTER TABLE public.orders OWNER TO toneflowers_migrator;
ALTER TABLE public.order_items OWNER TO toneflowers_migrator;
ALTER TABLE public.alembic_version OWNER TO toneflowers_migrator;
```

Verify any standalone sequences also have the intended migration owner. Do not
grant app membership in the migrator role. The app has DML and sequence usage,
not schema creation, DDL, superuser, database-creation or role-creation powers.
Default privileges affect only objects created by the named creator role; they
do not repair existing grants. See PostgreSQL's
[default privileges reference](https://www.postgresql.org/docs/18/sql-alterdefaultprivileges.html).

A single non-superuser owner role can simplify an initial small installation,
but it lets a compromised API alter or drop its tables. The two-role setup above
is the recommended simple choice: migrator credentials exist only during the
deployment step, while running API workers receive only the app credentials.
Managed providers may require their database administrator to apply these grants.

### Backups and restore tests

Enable automatic daily provider backups, retain at least **14 daily copies**,
and keep encrypted copies outside the API host. Enable point-in-time recovery
when available. A daily-only backup can lose up to 24 hours of orders; choose
the recovery window with the owner. Alert on backup failures. Take a fresh
backup before every migration and perform a restore test at least monthly.

Example manual pre-migration logical backup (PostgreSQL 18 client, migrator/backup
role with read access). Use an interactive password prompt or a protected
`PGPASSFILE`; never put passwords in command arguments or commit backup files:

```sh
pg_dump --host=DB_HOST --port=5432 --username=toneflowers_migrator --dbname=toneflowers --format=custom --file=toneflowers-before-migration.dump --no-password
pg_restore --list toneflowers-before-migration.dump
```

`--no-password` makes unattended jobs fail if credentials are missing; it does
not bypass authentication. Set libpq TLS variables (`PGSSLMODE=verify-full`,
`PGSSLROOTCERT` as needed) for the remote host. The SQLAlchemy
`postgresql+psycopg://` URL is not a `pg_dump` connection string. Timestamp/archive
each backup, check the command exit status and upload it to protected backup
storage. A dump contains customer data and does not include cluster roles;
keep the role setup separately. Logical dumps supplement provider backups.
See [pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html).

For a restore drill, have the operator create an **empty isolated** database
`toneflowers_restore_test` on `RESTORE_HOST` owned by `toneflowers_migrator`.
Review the destination before running this manually:

```sh
pg_restore --host=RESTORE_HOST --port=5432 --username=toneflowers_migrator --dbname=toneflowers_restore_test --no-owner --no-privileges --exit-on-error --single-transaction --no-password toneflowers-before-migration.dump
```

There is deliberately no `--clean` and no automated destructive restore.
Compare order/item counts, totals, stock, schema revision and health in the
restored database; reapply app grants if testing the runtime role. No live order
or email test should run against a restored customer database. A successful
`--list` alone is not a restore test. See
[pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html).

### Safe release sequence and server command

1. Confirm target database, environment and backup destination; take and check
   a fresh backup. For migrations incompatible with old code, stop accepting
   orders and gracefully drain API workers before changing the schema.
2. Run **one** deployment job with the migrator `DATABASE_URL`:
   `python -m alembic upgrade head`, followed by `python -m alembic check`.
   Stop the release if either fails. Reapply/review runtime table grants.
3. Start/restart API workers with the **app** `DATABASE_URL`, and check `/health`.
4. Build/publish the frontend with its matching API URL and complete staging
   checks before allowing real customer orders.

Migrations never run in requests or application worker startup. Concurrent
workers running DDL can race and lock each other. Existing migrations deliberately
refuse destructive downgrades; review recovery from backups/forward fixes before
release instead of assuming `alembic downgrade` is safe.

Linux/platform shell, with `PORT` supplied by hosting:

```sh
python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --no-access-log --timeout-graceful-shutdown 30
```

PowerShell equivalent (set `PORT` in the service environment):

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port $env:PORT --workers 1 --no-access-log --timeout-graceful-shutdown 30
```

Do not use `--reload` in staging/production. Start with one worker for small-shop
traffic. Consider two only after measuring memory, CPU, request latency and
PostgreSQL connection capacity; each worker has its own SQLAlchemy pool. Use
the platform's process supervision/restart policy, not a new local daemon or
Gunicorn dependency. Give the platform at least the graceful shutdown interval.
Confirm target-specific Uvicorn/proxy settings with the
[Uvicorn reference](https://www.uvicorn.org/settings/).

### Logging and customer-facing errors

Startup/shutdown and environment mode are logged. Failures log a safe operation
description, exception type and code filename/line. They deliberately omit
exception text, SQL values, headers, request bodies and customer details. SQL
parameters are hidden on the runtime engine. Unexpected API failures return
generic JSON `500`; health database failures return `503`. Expected validation,
stock, product, delivery-region and replay-conflict errors retain their existing
HTTP behavior. Debug responses are disabled.

The production command disables access logs to avoid recording client IPs and
query strings unnecessarily. Configure hosting/proxy logs similarly: never log
`X-Admin-Key`, credentials, request bodies or full database URLs. Store operational
logs with restricted access and retention. Safe logs trade detailed exception
messages for privacy; reproduce failures with synthetic data for diagnosis.

### Email setup and delivery limits

The locally verified path uses Gmail SMTP on port 587 with STARTTLS and a Gmail
App Password. Both owner recipients remain configured privately in
`SHOP_NOTIFICATION_EMAILS`; neither address belongs in public examples. The
previous approved local order reached SMTP acceptance for both recipients and
inbox receipt was confirmed for one; the other owner's inbox confirmation is
still outstanding. No email is sent by this preparation task or automated tests.

At staging launch, obtain authorization for a clearly marked TEST ONLY order
and confirm receipt in **both** owner inboxes. `notified_at` means SMTP accepted
all recipients; it does not prove inbox delivery. Partial recipient refusal can
mean one recipient already received the email. Do not blindly resend.

Notifications run in the existing in-process background task. Graceful shutdown
usually lets tasks finish, but a crash can lose a notification and there is no
automatic retry. The owner must check the private order list and investigate
null `notified_at` records; never rely solely on email for fulfillment. SMTP
acceptance followed by a marker-write failure can also leave that value null.

### Frontend production build and SPA routing

`WHATSAPP_NUMBER` and `VODAFONE_CASH_NUMBER` are returned by `GET /public-config`
because they are customer-facing payment/contact details. No admin or mail
credentials are included in that response. Local business values belong in the
ignored backend `.env`; `.env.example` contains placeholders only.

Product image values stay in `image_url`; admins can upload JPEG, PNG, and WebP
images up to 5 MB or keep using an external HTTP(S) image URL. Development files
are stored under `media/products/`. Production uploads are disabled unless a
persistent disk is mounted at `MEDIA_DIR` and `MEDIA_PERSISTENT_STORAGE=true` is
explicitly set. Configure backups and serve that disk at `MEDIA_BASE_URL`.
Ephemeral container storage is not durable. No cloud storage vendor is
integrated; use approved external image URLs until persistent media is ready.
Demo products have no photos and use the storefront placeholder.

The API base is configured in one place, `frontend/src/config.ts`, through
`VITE_API_URL`. Its localhost fallback is for development; components contain
no localhost API URLs. Set the real API URL **before** building. Set
`VITE_SITE_URL` only after the real frontend origin is selected; when it is
empty, the app emits no canonical URL. Vite substitutes public variables at
build time, so changing the host environment after building does not update an
existing bundle; rebuild it.

```dotenv
VITE_API_URL=https://api.example.com
VITE_SITE_URL=
VITE_PHONE=PUBLIC_SHOP_PHONE
VITE_EMAIL=public-contact@example.com
VITE_FACEBOOK_URL=https://www.facebook.com/YOUR_PUBLIC_PAGE
VITE_INSTAGRAM_URL=
VITE_WHATSAPP_URL=
```

Set only intentional public contact details. WhatsApp and Vodafone Cash numbers
are configured on the backend and returned by `/public-config`; keep them out
of `VITE_` variables. All `VITE_` values are visible to visitors. No database
URL, admin key, session secret, password hash or SMTP credential goes here.

```sh
cd frontend
npm ci
npm run build
```

Serve `frontend/dist/` from static hosting. Configure an internal fallback to
`index.html` for unmatched application routes, after checking real static files.
Direct visits/refreshes to `/products/3`, `/checkout` and `/about` must load React
Router instead of a hosting 404. Keep API routing and missing asset handling
separate from the SPA fallback. No provider-specific config is created until a
deployment target is chosen.

### Staging launch checklist

- [ ] Choose frontend/API hosting and a separate production-like PostgreSQL staging database.
- [ ] Configure restricted app/migration roles; verify app DML works and DDL is denied.
- [ ] Configure all real backend variables and `APP_ENV=staging`; generate a fresh strong admin key.
- [ ] Configure the browser-admin login email, PBKDF2 password hash and session secret; verify login/logout and CSRF rejection.
- [ ] Run `python -m backend.seed_catalog`; verify active Cairo/Giza zones show 50.00 EGP.
- [ ] Seed demo products only in development/staging; run `python -m backend.remove_demo_catalog` before public launch.
- [ ] Configure persistent media before enabling uploads; otherwise keep uploads disabled and use approved image URLs.
- [ ] Configure exact HTTPS CORS origins and build-time `VITE_API_URL`.
- [ ] Enable HTTPS for frontend/API and verify database TLS/network restrictions.
- [ ] Verify automatic backups, retention, pre-migration backup and an isolated restore drill.
- [ ] Apply migrations once with the migrator role; `alembic check` passes.
- [ ] Start the API with the app role; unauthenticated `GET /health` returns 200.
- [ ] Verify sensitive order routes reject missing/wrong keys and unauthenticated sessions; confirm browser session access works.
- [ ] Replace demo products with real Arabic/English names, approved images and real prices.
- [ ] Check direct SPA routes, refreshes and mobile checkout on a real device.
- [ ] With owner approval, place one TEST ONLY order; verify fields, backend total, Cairo time, pending availability confirmation and no stock mutation.
- [ ] Confirm one notification in both owner inboxes and non-null `notified_at`.
- [ ] Verify the test order in the private admin list.
- [ ] Confirm availability, progress status, verify payment, and test cancellation without stock mutation; verify the manual-refund warning for paid cancellation.
- [ ] Verify same-key replay/conflict behavior and no duplicate notification.
- [ ] Review sanitized logs, restart behavior and the owner's manual notification-failure procedure.
- [ ] Complete all checks before a separate production deployment approval.

Remaining launch blockers: choose hosting and real frontend/API origins, provision
environment-specific database/roles/secrets, enable HTTPS and backups, configure
persistent media or keep uploads disabled, confirm both recipient inboxes,
replace demo products/prices, verify image rights, and complete authorized
staging/mobile checks. No production deployment or external configuration has
been performed here.

The existing logo and homepage floral photograph were present before this pass;
their commercial usage rights are not established in this repository. Confirm
rights with the shop owner before public launch.
