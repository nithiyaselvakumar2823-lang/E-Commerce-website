# Fieldstore — Full-Stack E-Commerce App

A from-scratch online store built with **Flask**, **SQLite**, and vanilla
**HTML/CSS/JS**. Product catalog, cart, checkout, order tracking, and a
role-based admin dashboard — all backed by a plain REST API.

## Why SQLite instead of MySQL/PostgreSQL/MongoDB?

SQLite ships built into Python, so the project runs with **zero database
setup** — perfect for coursework and demos. Everything talks to the
database only through `database.py`, so swapping the engine later is a
contained change, not a rewrite. See **"Switching databases"** below.

## Quick start

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000**. The database (`store.db`) and sample data
are created automatically on first run.

**Demo accounts** (also printed in the terminal on startup):
| Role  | Username | Password  |
|-------|----------|-----------|
| Admin | `admin`  | `admin123`|
| User  | `demo`   | `demo1234`|

## What's included

- **Catalog** — search, category filters, stock badges
- **Cart** — slide-in drawer, quantity controls, stock-aware
- **Checkout** — address form, order created from cart, stock decremented
- **Order history** — per-user order list with status and line items
- **Admin dashboard** (role = `admin`) — revenue/orders/products stats,
  full product CRUD, and order status management (Pending → Processing →
  Shipped → Delivered / Cancelled)
- **Auth** — registration, login/logout, hashed passwords
  (`werkzeug.security`), session-based access control

## Project structure

```
ecommerce_app/
├── app.py              # Flask app: all routes + REST API
├── database.py         # SQLite schema + connection helper
├── requirements.txt
├── store.db             # created automatically on first run
├── templates/
│   └── index.html      # single-page shell (shop / orders / admin views)
└── static/
    ├── css/style.css   # all styling
    └── js/app.js       # all frontend logic (fetch calls + rendering)
```

## API reference

All endpoints return JSON. Endpoints marked 🔒 require login,
🔒🛡️ require an admin account.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/register` | Create an account |
| POST | `/api/login` | Log in |
| POST | `/api/logout` | 🔒 Log out |
| GET | `/api/me` | Current session user |
| GET | `/api/products` | List products (`?category=`, `?search=`) |
| GET | `/api/products/<id>` | Product detail |
| POST | `/api/products` | 🔒🛡️ Create product |
| PUT | `/api/products/<id>` | 🔒🛡️ Update product |
| DELETE | `/api/products/<id>` | 🔒🛡️ Delete product |
| GET | `/api/cart` | 🔒 View cart |
| POST | `/api/cart` | 🔒 Add item |
| PUT | `/api/cart/<item_id>` | 🔒 Change quantity |
| DELETE | `/api/cart/<item_id>` | 🔒 Remove item |
| POST | `/api/orders/checkout` | 🔒 Place order from cart |
| GET | `/api/orders` | 🔒 List own orders (admin: `?all=1` for every order) |
| GET | `/api/orders/<id>` | 🔒 Order detail with line items |
| PUT | `/api/admin/orders/<id>/status` | 🔒🛡️ Update order status |
| GET | `/api/admin/stats` | 🔒🛡️ Dashboard totals + low-stock list |

## Switching databases

Everything database-related lives in `database.py`. To move to MySQL or
PostgreSQL:

1. `pip install mysql-connector-python` (or `psycopg2-binary`)
2. In `database.py`, replace `sqlite3.connect(DB_PATH)` in `get_db()`
   with the equivalent connector call (host/user/password/db name).
3. In the `SCHEMA` string, change `INTEGER PRIMARY KEY AUTOINCREMENT` to
   `INT AUTO_INCREMENT PRIMARY KEY` (MySQL) or `SERIAL PRIMARY KEY`
   (PostgreSQL).
4. Nothing in `app.py` needs to change — it only calls `get_db()` and
   runs SQL, which stays the same.

For MongoDB you'd replace the SQL calls with PyMongo document operations;
because `app.py` treats `database.py` as a black box, only that file
would need a rewrite.

## Ideas to extend it

- Product images: file upload instead of URLs
- Pagination on the catalog and admin tables
- Email confirmation on checkout
- Coupon codes / discounts
- Product reviews and ratings
- Unit tests with `pytest` against the Flask test client
