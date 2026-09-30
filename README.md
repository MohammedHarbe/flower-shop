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
columns. It does not delete old products or orders. Historical orders have a
null governorate when it could not be determined; new orders require Cairo or
Giza. SQLite remains the development default. Set `DATABASE_URL` to a
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
  with item `product_id` and `quantity`. Send `governorate` as `Cairo` or `Giza`.
  Do not send price, total, status, or server-generated IDs.
- `GET /orders/{id}` and `PATCH /orders/{id}/status` require `X-Admin-Key`.

At checkout, the website refreshes product availability and sends IDs and
quantities. FastAPI validates the order; SQLAlchemy calculates prices, stores
items, and reduces stock in one transaction. After commit, a background task
sends the owner email. A mail failure is logged and cannot undo the order.
The success page uses the `POST /orders` response, so it does not fetch private
order details through a sequential public ID.

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
