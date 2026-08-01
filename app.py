"""
app.py — Flask backend for the store.

Run with:
    python app.py
Then open http://127.0.0.1:5000

First run automatically creates store.db and seeds sample data + an
admin account (username: admin / password: admin123).
"""

from functools import wraps
from flask import Flask, jsonify, request, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re

from database import get_db, init_db, DB_PATH

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Startup: create + seed the database on first run
# ---------------------------------------------------------------------------
def ensure_seeded():
    init_db()
    db = get_db()
    try:
        has_users = db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        if has_users == 0:
            db.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?,?,?,?)",
                ("admin", "admin@store.local", generate_password_hash("admin123"), "admin"),
            )
            db.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?,?,?,?)",
                ("demo", "demo@store.local", generate_password_hash("demo1234"), "user"),
            )

        has_products = db.execute("SELECT COUNT(*) c FROM products").fetchone()["c"]
        if has_products == 0:
            sample = [
                ("Ceramic Pour-Over Set", "Hand-glazed stoneware dripper with matching mug. Slow mornings, made simple.", 1499.00, "Kitchen", 24, "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=600"),
                ("Linen Weekender Bag", "Washed linen duffel with leather straps. Holds a weekend, weighs nothing.", 3299.00, "Bags", 12, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600"),
                ("Brass Desk Lamp", "Adjustable brass arm lamp with a warm 2700K bulb included.", 2199.00, "Home", 18, "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600"),
                ("Wool Throw Blanket", "Heavyweight merino throw, woven in a small mill. Six colourways.", 2799.00, "Home", 30, "https://images.unsplash.com/photo-1580301762395-83bc60ed4a7e?w=600"),
                ("Field Notebook Trio", "Three pocket notebooks, dot-grid pages, rounded corners.", 449.00, "Stationery", 60, "https://images.unsplash.com/photo-1531346680769-a1d79b57de5c?w=600"),
                ("Enamel Camp Mug", "12oz enamel mug that survives campfires and dishwashers.", 349.00, "Kitchen", 45, "https://images.unsplash.com/photo-1577937927133-66ef06acdf18?w=600"),
                ("Canvas Apron", "Waxed canvas apron with a brass buckle and two deep pockets.", 1199.00, "Kitchen", 20, "https://images.unsplash.com/photo-1622480916113-9000ac49b79d?w=600"),
                ("Terrazzo Coasters", "Set of four handcast terrazzo coasters with cork backing.", 699.00, "Home", 40, "https://images.unsplash.com/photo-1567016432779-094069958ea5?w=600"),
                ("Walnut Cutting Board", "Edge-grain walnut board, oiled and ready to use.", 1899.00, "Kitchen", 15, "https://images.unsplash.com/photo-1541599468348-e96984315921?w=600"),
                ("Cotton Market Tote", "Heavyweight cotton canvas tote, reinforced base.", 599.00, "Bags", 50, "https://images.unsplash.com/photo-1591561954557-26941169b49e?w=600"),
                ("Recycled Glass Vase", "Hand-blown from recycled glass, no two exactly alike.", 999.00, "Home", 22, "https://images.unsplash.com/photo-1578500494198-246f612d3b3d?w=600"),
                ("Leather Cardholder", "Full-grain leather cardholder that ages beautifully.", 799.00, "Bags", 35, "https://images.unsplash.com/photo-1627123424574-724758594e93?w=600"),
            ]
            db.executemany(
                "INSERT INTO products (name, description, price, category, stock, image_url) VALUES (?,?,?,?,?,?)",
                sample,
            )
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Please log in to continue."}), 401
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Please log in to continue."}), 401
        if session.get("role") != "admin":
            return jsonify({"error": "Admin access required."}), 403
        return fn(*args, **kwargs)
    return wrapper


def current_user_public():
    if "user_id" not in session:
        return None
    return {"id": session["user_id"], "username": session["username"], "role": session["role"]}


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Auth API
# ---------------------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    db = get_db()
    try:
        existing = db.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?", (username, email)
        ).fetchone()
        if existing:
            return jsonify({"error": "That username or email is already registered."}), 409

        cur = db.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?,?,?,'user')",
            (username, email, generate_password_hash(password)),
        )
        db.commit()
        user_id = cur.lastrowid
        session["user_id"] = user_id
        session["username"] = username
        session["role"] = "user"
        return jsonify({"user": current_user_public()}), 201
    finally:
        db.close()


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    db = get_db()
    try:
        user = db.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?", (username, username)
        ).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid username or password."}), 401

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        return jsonify({"user": current_user_public()})
    finally:
        db.close()


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/me")
def me():
    return jsonify({"user": current_user_public()})


# ---------------------------------------------------------------------------
# Product API
# ---------------------------------------------------------------------------
@app.route("/api/products", methods=["GET"])
def list_products():
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip()

    query = "SELECT * FROM products WHERE 1=1"
    params = []
    if category and category != "All":
        query += " AND category = ?"
        params.append(category)
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])
    query += " ORDER BY created_at DESC"

    db = get_db()
    try:
        products = [dict(row) for row in db.execute(query, params).fetchall()]
        categories = [r["category"] for r in db.execute(
            "SELECT DISTINCT category FROM products ORDER BY category"
        ).fetchall()]
        return jsonify({"products": products, "categories": categories})
    finally:
        db.close()


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    db = get_db()
    try:
        product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            return jsonify({"error": "Product not found."}), 404
        return jsonify({"product": dict(product)})
    finally:
        db.close()


def _validate_product_payload(data, partial=False):
    errors = []
    fields = {}
    if "name" in data or not partial:
        name = (data.get("name") or "").strip()
        if len(name) < 2:
            errors.append("Name must be at least 2 characters.")
        fields["name"] = name
    if "description" in data or not partial:
        fields["description"] = (data.get("description") or "").strip()
    if "price" in data or not partial:
        try:
            price = float(data.get("price"))
            if price < 0:
                raise ValueError
        except (TypeError, ValueError):
            errors.append("Price must be a non-negative number.")
            price = 0
        fields["price"] = price
    if "category" in data or not partial:
        fields["category"] = (data.get("category") or "General").strip() or "General"
    if "stock" in data or not partial:
        try:
            stock = int(data.get("stock"))
            if stock < 0:
                raise ValueError
        except (TypeError, ValueError):
            errors.append("Stock must be a non-negative whole number.")
            stock = 0
        fields["stock"] = stock
    if "image_url" in data or not partial:
        fields["image_url"] = (data.get("image_url") or "").strip()
    return fields, errors


@app.route("/api/products", methods=["POST"])
@admin_required
def create_product():
    data = request.get_json(silent=True) or {}
    fields, errors = _validate_product_payload(data)
    if errors:
        return jsonify({"error": " ".join(errors)}), 400

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO products (name, description, price, category, stock, image_url) "
            "VALUES (?,?,?,?,?,?)",
            (fields["name"], fields["description"], fields["price"],
             fields["category"], fields["stock"], fields["image_url"]),
        )
        db.commit()
        product = db.execute("SELECT * FROM products WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify({"product": dict(product)}), 201
    finally:
        db.close()


@app.route("/api/products/<int:product_id>", methods=["PUT"])
@admin_required
def update_product(product_id):
    data = request.get_json(silent=True) or {}
    fields, errors = _validate_product_payload(data, partial=True)
    if errors:
        return jsonify({"error": " ".join(errors)}), 400
    if not fields:
        return jsonify({"error": "No fields to update."}), 400

    db = get_db()
    try:
        existing = db.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
        if not existing:
            return jsonify({"error": "Product not found."}), 404

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        params = list(fields.values()) + [product_id]
        db.execute(f"UPDATE products SET {set_clause} WHERE id = ?", params)
        db.commit()
        product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return jsonify({"product": dict(product)})
    finally:
        db.close()


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
@admin_required
def delete_product(product_id):
    db = get_db()
    try:
        existing = db.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
        if not existing:
            return jsonify({"error": "Product not found."}), 404
        db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Cart API (per logged-in user)
# ---------------------------------------------------------------------------
def _serialise_cart(db, user_id):
    rows = db.execute(
        """SELECT ci.id AS cart_item_id, ci.quantity, p.id AS product_id, p.name,
                  p.price, p.image_url, p.stock
           FROM cart_items ci JOIN products p ON p.id = ci.product_id
           WHERE ci.user_id = ? ORDER BY ci.id""",
        (user_id,),
    ).fetchall()
    items = [dict(r) for r in rows]
    subtotal = sum(i["price"] * i["quantity"] for i in items)
    return items, round(subtotal, 2)


@app.route("/api/cart", methods=["GET"])
@login_required
def get_cart():
    db = get_db()
    try:
        items, subtotal = _serialise_cart(db, session["user_id"])
        return jsonify({"items": items, "subtotal": subtotal})
    finally:
        db.close()


@app.route("/api/cart", methods=["POST"])
@login_required
def add_to_cart():
    data = request.get_json(silent=True) or {}
    try:
        product_id = int(data.get("product_id"))
        quantity = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid product or quantity."}), 400
    if quantity < 1:
        return jsonify({"error": "Quantity must be at least 1."}), 400

    db = get_db()
    try:
        product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            return jsonify({"error": "Product not found."}), 404

        existing = db.execute(
            "SELECT * FROM cart_items WHERE user_id = ? AND product_id = ?",
            (session["user_id"], product_id),
        ).fetchone()
        new_qty = quantity + (existing["quantity"] if existing else 0)
        if new_qty > product["stock"]:
            return jsonify({"error": f"Only {product['stock']} in stock."}), 400

        if existing:
            db.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (new_qty, existing["id"]))
        else:
            db.execute(
                "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?,?,?)",
                (session["user_id"], product_id, quantity),
            )
        db.commit()
        items, subtotal = _serialise_cart(db, session["user_id"])
        return jsonify({"items": items, "subtotal": subtotal}), 201
    finally:
        db.close()


@app.route("/api/cart/<int:cart_item_id>", methods=["PUT"])
@login_required
def update_cart_item(cart_item_id):
    data = request.get_json(silent=True) or {}
    try:
        quantity = int(data.get("quantity"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid quantity."}), 400

    db = get_db()
    try:
        item = db.execute(
            "SELECT * FROM cart_items WHERE id = ? AND user_id = ?",
            (cart_item_id, session["user_id"]),
        ).fetchone()
        if not item:
            return jsonify({"error": "Cart item not found."}), 404

        if quantity < 1:
            db.execute("DELETE FROM cart_items WHERE id = ?", (cart_item_id,))
        else:
            product = db.execute("SELECT stock FROM products WHERE id = ?", (item["product_id"],)).fetchone()
            if product and quantity > product["stock"]:
                return jsonify({"error": f"Only {product['stock']} in stock."}), 400
            db.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (quantity, cart_item_id))
        db.commit()
        items, subtotal = _serialise_cart(db, session["user_id"])
        return jsonify({"items": items, "subtotal": subtotal})
    finally:
        db.close()


@app.route("/api/cart/<int:cart_item_id>", methods=["DELETE"])
@login_required
def remove_cart_item(cart_item_id):
    db = get_db()
    try:
        db.execute(
            "DELETE FROM cart_items WHERE id = ? AND user_id = ?",
            (cart_item_id, session["user_id"]),
        )
        db.commit()
        items, subtotal = _serialise_cart(db, session["user_id"])
        return jsonify({"items": items, "subtotal": subtotal})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Order API
# ---------------------------------------------------------------------------
@app.route("/api/orders/checkout", methods=["POST"])
@login_required
def checkout():
    data = request.get_json(silent=True) or {}
    shipping_address = (data.get("shipping_address") or "").strip()
    if len(shipping_address) < 5:
        return jsonify({"error": "Please enter a valid shipping address."}), 400

    db = get_db()
    try:
        items, subtotal = _serialise_cart(db, session["user_id"])
        if not items:
            return jsonify({"error": "Your cart is empty."}), 400

        for item in items:
            product = db.execute("SELECT stock FROM products WHERE id = ?", (item["product_id"],)).fetchone()
            if not product or item["quantity"] > product["stock"]:
                return jsonify({"error": f"'{item['name']}' no longer has enough stock."}), 400

        cur = db.execute(
            "INSERT INTO orders (user_id, total_amount, status, shipping_address) VALUES (?,?,?,?)",
            (session["user_id"], subtotal, "Pending", shipping_address),
        )
        order_id = cur.lastrowid

        for item in items:
            db.execute(
                "INSERT INTO order_items (order_id, product_id, product_name, price_at_purchase, quantity) "
                "VALUES (?,?,?,?,?)",
                (order_id, item["product_id"], item["name"], item["price"], item["quantity"]),
            )
            db.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )

        db.execute("DELETE FROM cart_items WHERE user_id = ?", (session["user_id"],))
        db.commit()

        order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return jsonify({"order": dict(order)}), 201
    finally:
        db.close()


@app.route("/api/orders", methods=["GET"])
@login_required
def list_orders():
    db = get_db()
    try:
        show_all = request.args.get("all") == "1" and session.get("role") == "admin"
        if show_all:
            orders = db.execute(
                """SELECT o.*, u.username FROM orders o
                   JOIN users u ON u.id = o.user_id ORDER BY o.created_at DESC"""
            ).fetchall()
        else:
            orders = db.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
                (session["user_id"],),
            ).fetchall()
        return jsonify({"orders": [dict(o) for o in orders]})
    finally:
        db.close()


@app.route("/api/orders/<int:order_id>", methods=["GET"])
@login_required
def get_order(order_id):
    db = get_db()
    try:
        order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            return jsonify({"error": "Order not found."}), 404
        if order["user_id"] != session["user_id"] and session.get("role") != "admin":
            return jsonify({"error": "Not authorised to view this order."}), 403
        items = db.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
        return jsonify({"order": dict(order), "items": [dict(i) for i in items]})
    finally:
        db.close()


@app.route("/api/admin/orders/<int:order_id>/status", methods=["PUT"])
@admin_required
def update_order_status(order_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    valid = {"Pending", "Processing", "Shipped", "Delivered", "Cancelled"}
    if status not in valid:
        return jsonify({"error": f"Status must be one of {', '.join(valid)}."}), 400

    db = get_db()
    try:
        existing = db.execute("SELECT id FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not existing:
            return jsonify({"error": "Order not found."}), 404
        db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        db.commit()
        order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return jsonify({"order": dict(order)})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Admin dashboard stats
# ---------------------------------------------------------------------------
@app.route("/api/admin/stats")
@admin_required
def admin_stats():
    db = get_db()
    try:
        revenue = db.execute(
            "SELECT COALESCE(SUM(total_amount),0) r FROM orders WHERE status != 'Cancelled'"
        ).fetchone()["r"]
        order_count = db.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"]
        product_count = db.execute("SELECT COUNT(*) c FROM products").fetchone()["c"]
        user_count = db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        low_stock = db.execute(
            "SELECT id, name, stock FROM products WHERE stock <= 5 ORDER BY stock ASC"
        ).fetchall()
        return jsonify({
            "revenue": round(revenue, 2),
            "order_count": order_count,
            "product_count": product_count,
            "user_count": user_count,
            "low_stock": [dict(r) for r in low_stock],
        })
    finally:
        db.close()


if __name__ == "__main__":
    ensure_seeded()
    print(f"Database ready at {DB_PATH}")
    print("Admin login  -> username: admin  password: admin123")
    print("Demo user    -> username: demo   password: demo1234")
    app.run(debug=True, host="127.0.0.1", port=5000)
