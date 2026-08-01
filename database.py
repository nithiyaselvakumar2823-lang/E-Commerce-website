"""
database.py
Handles all SQLite connection & schema setup for the store.

NOTE ON SWAPPING DATABASES:
This project uses SQLite (Python's built-in `sqlite3` module) so it runs
anywhere with zero setup. If your course requires MySQL or PostgreSQL,
you only need to change this file:
  - MySQL: install `mysql-connector-python`, swap sqlite3.connect() for
    mysql.connector.connect(host=..., user=..., password=..., database=...)
  - PostgreSQL: install `psycopg2`, swap sqlite3.connect() for
    psycopg2.connect(dbname=..., user=..., password=..., host=...)
  - The SQL below is close to standard ANSI SQL; only AUTOINCREMENT
    (-> AUTO_INCREMENT / SERIAL) and a couple of type names would need
    small edits. Every route in app.py talks to database.py only, never
    to raw SQL directly, so the rest of the app doesn't need to change.
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "store.db")


def get_db():
    """Open a new connection with rows returned as dict-like objects."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user', 'admin')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price REAL NOT NULL CHECK(price >= 0),
    category TEXT NOT NULL DEFAULT 'General',
    stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
    image_url TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity > 0),
    UNIQUE(user_id, product_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_amount REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending'
        CHECK(status IN ('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled')),
    shipping_address TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    product_name TEXT NOT NULL,
    price_at_purchase REAL NOT NULL,
    quantity INTEGER NOT NULL
);
"""


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialised at {DB_PATH}")
