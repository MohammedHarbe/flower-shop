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
