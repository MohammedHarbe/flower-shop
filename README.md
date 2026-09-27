# ToneFlowers backend

FastAPI backend for products and flower orders. SQLite is used during development.

## Run locally (PowerShell)

```powershell
cd 'C:\Users\mohamed harbe\flower-shop'
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uvicorn backend.main:app --reload
```

Fill in the email settings in `.env` before testing notifications. `SMTP_PASSWORD`
should be a Gmail App Password. The sender is `SMTP_USERNAME`; the recipient is
`SHOP_NOTIFICATION_EMAIL`. Open `http://127.0.0.1:8000/docs` for Swagger UI.

## Order endpoints

- `POST /orders` validates the whole order, saves item prices and totals on the
  server, and reduces stock in one database transaction. Duplicate product IDs
  are rejected. A successful response has status 201.
- `GET /orders/{order_id}` returns the order and its saved items.
- `PATCH /orders/{order_id}/status` accepts one of `pending`, `confirmed`,
  `preparing`, `out_for_delivery`, `delivered`, or `cancelled`.

Notifications are queued after an order commits. A Gmail failure is logged and
does not undo the order. The status endpoint needs admin authentication before
production use.

Run the order tests with `python -m unittest discover -s tests -v`.
