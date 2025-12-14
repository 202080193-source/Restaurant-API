from flask import Flask, request, jsonify, make_response
from flask_bcrypt import Bcrypt
import MySQLdb
import MySQLdb.cursors
import datetime
import os
import xmltodict

# ---------------------------
# App setup
# ---------------------------
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "supersecretkey123")

# ---------------------------
# Database connection
# ---------------------------
DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "root"
DB_NAME = "restaurant_db"  # Change to your DB name

def get_db_connection():
    return MySQLdb.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        cursorclass=MySQLdb.cursors.DictCursor,
        autocommit=False,
        charset="utf8mb4"
    )

def get_cursor():
    conn = get_db_connection()
    return conn, conn.cursor()

# ---------------------------
# Helper: JSON/XML response
# ---------------------------
def respond(data, status=200):
    fmt = (request.args.get("format") or "json").lower()
    if fmt == "xml":
        xml_data = xmltodict.unparse({"response": {"item": data}}, pretty=True)
        response = make_response(xml_data, status)
        response.headers["Content-Type"] = "application/xml"
        return response
    # Default JSON
    response = make_response(jsonify(data), status)
    response.headers["Content-Type"] = "application/json"
    return response

# ---------------------------
# Menu CRUD
# ---------------------------
@app.route("/menu", methods=["GET", "POST"])
def menu_collection():
    if request.method == "GET":
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT menu_id, item_name, category, price FROM menu")
            items = cur.fetchall()
        finally:
            cur.close()
            conn.close()
        return respond({"menu": items})

    data = request.json or {}
    item_name = (data.get("item_name") or "").strip()
    category = (data.get("category") or "").strip()
    price = data.get("price")

    if not item_name or not category or price is None:
        return respond({"msg": "item_name, category, and price are required"}, 400)

    try:
        price = float(price)
        if price < 0:
            raise ValueError()
    except Exception:
        return respond({"msg": "price must be a positive number"}, 400)

    conn, cur = get_cursor()
    try:
        cur.execute("SELECT 1 FROM menu WHERE item_name=%s", (item_name,))
        if cur.fetchone():
            return respond({"msg": "menu item already exists"}, 409)
        cur.execute("INSERT INTO menu (item_name, category, price) VALUES (%s, %s, %s)",
                    (item_name, category, price))
        conn.commit()
        new_id = cur.lastrowid
    finally:
        cur.close()
        conn.close()
    return respond({"menu_id": new_id, "item_name": item_name, "category": category, "price": price}, 201)

@app.route("/menu/<int:menu_id>", methods=["GET", "PUT", "DELETE"])
def menu_detail(menu_id):
    conn, cur = get_cursor()
    try:
        cur.execute("SELECT menu_id, item_name, category, price FROM menu WHERE menu_id=%s", (menu_id,))
        item = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if request.method == "GET":
        if not item:
            return respond({"msg": "menu item not found"}, 404)
        return respond(item)

    data = request.json or {}
    item_name = (data.get("item_name") or "").strip()
    category = (data.get("category") or "").strip()
    price = data.get("price")

    if request.method == "PUT":
        if not item_name or not category or price is None:
            return respond({"msg": "item_name, category, and price required"}, 400)
        try:
            price = float(price)
            if price < 0:
                raise ValueError()
        except Exception:
            return respond({"msg": "price must be positive number"}, 400)
        conn, cur = get_cursor()
        try:
            cur.execute("UPDATE menu SET item_name=%s, category=%s, price=%s WHERE menu_id=%s",
                        (item_name, category, price, menu_id))
            if cur.rowcount == 0:
                return respond({"msg": "menu item not found"}, 404)
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return respond({"menu_id": menu_id, "item_name": item_name, "category": category, "price": price})

    if request.method == "DELETE":
        conn, cur = get_cursor()
        try:
            cur.execute("DELETE FROM menu WHERE menu_id=%s", (menu_id,))
            if cur.rowcount == 0:
                return respond({"msg": "menu item not found"}, 404)
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return '', 204

# ---------------------------
# Customers CRUD
# ---------------------------
@app.route("/customers", methods=["GET", "POST"])
def customers_collection():
    if request.method == "GET":
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT customer_id, customer_name, phone_number, email FROM customers")
            customers = cur.fetchall()
        finally:
            cur.close()
            conn.close()
        return respond({"customers": customers})

    data = request.json or {}
    customer_name = (data.get("customer_name") or "").strip()
    phone_number = (data.get("phone_number") or "").strip()
    email = (data.get("email") or "").strip()

    if not customer_name or not email:
        return respond({"msg": "customer_name and email required"}, 400)

    conn, cur = get_cursor()
    try:
        cur.execute("SELECT 1 FROM customers WHERE email=%s", (email,))
        if cur.fetchone():
            return respond({"msg": "customer email already exists"}, 409)
        cur.execute("INSERT INTO customers (customer_name, phone_number, email) VALUES (%s, %s, %s)",
                    (customer_name, phone_number, email))
        conn.commit()
        new_id = cur.lastrowid
    finally:
        cur.close()
        conn.close()
    return respond({"customer_id": new_id, "customer_name": customer_name, "phone_number": phone_number, "email": email}, 201)

@app.route("/customers/<int:customer_id>", methods=["GET", "PUT", "DELETE"])
def customer_detail(customer_id):
    conn, cur = get_cursor()
    try:
        cur.execute("SELECT customer_id, customer_name, phone_number, email FROM customers WHERE customer_id=%s", (customer_id,))
        customer = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if request.method == "GET":
        if not customer:
            return respond({"msg": "customer not found"}, 404)
        return respond(customer)

    data = request.json or {}
    customer_name = (data.get("customer_name") or "").strip()
    phone_number = (data.get("phone_number") or "").strip()
    email = (data.get("email") or "").strip()

    if request.method == "PUT":
        if not customer_name or not email:
            return respond({"msg": "customer_name and email required"}, 400)
        conn, cur = get_cursor()
        try:
            cur.execute("UPDATE customers SET customer_name=%s, phone_number=%s, email=%s WHERE customer_id=%s",
                        (customer_name, phone_number, email, customer_id))
            if cur.rowcount == 0:
                return respond({"msg": "customer not found"}, 404)
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return respond({"customer_id": customer_id, "customer_name": customer_name, "phone_number": phone_number, "email": email})

    if request.method == "DELETE":
        conn, cur = get_cursor()
        try:
            cur.execute("DELETE FROM customers WHERE customer_id=%s", (customer_id,))
            if cur.rowcount == 0:
                return respond({"msg": "customer not found"}, 404)
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return '', 204

# ---------------------------
# Orders CRUD
# ---------------------------
@app.route("/orders", methods=["GET", "POST"])
def orders_collection():
    if request.method == "GET":
        conn, cur = get_cursor()
        try:
            cur.execute("""
                SELECT o.order_id, c.customer_name, m.item_name, o.order_date, o.quantity
                FROM orders o
                JOIN customers c ON o.customer_id=c.customer_id
                JOIN menu m ON o.menu_id=m.menu_id
            """)
            orders = cur.fetchall()
        finally:
            cur.close()
            conn.close()
        return respond({"orders": orders})

    data = request.json or {}
    customer_id = data.get("customer_id")
    menu_id = data.get("menu_id")
    order_date = data.get("order_date")
    quantity = data.get("quantity", 1)

    if not customer_id or not menu_id or not order_date:
        return respond({"msg": "customer_id, menu_id, and order_date are required"}, 400)

    try:
        datetime.date.fromisoformat(order_date)
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError()
    except Exception:
        return respond({"msg": "invalid order_date or quantity"}, 400)

    conn, cur = get_cursor()
    try:
        cur.execute("INSERT INTO orders (customer_id, menu_id, order_date, quantity) VALUES (%s,%s,%s,%s)",
                    (customer_id, menu_id, order_date, quantity))
        conn.commit()
        new_id = cur.lastrowid
    finally:
        cur.close()
        conn.close()
    return respond({"order_id": new_id}, 201)

@app.route("/orders/<int:order_id>", methods=["GET", "PUT", "DELETE"])
def order_detail(order_id):
    conn, cur = get_cursor()
    try:
        cur.execute("SELECT * FROM orders WHERE order_id=%s", (order_id,))
        order = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if request.method == "GET":
        if not order:
            return respond({"msg": "order not found"}, 404)
        return respond(order)

    data = request.json or {}
    customer_id = data.get("customer_id")
    menu_id = data.get("menu_id")
    order_date = data.get("order_date")
    quantity = data.get("quantity")

    if request.method == "PUT":
        fields, params = [], []
        if customer_id: 
            fields.append("customer_id=%s")
            params.append(customer_id)
        if menu_id:
            fields.append("menu_id=%s")
            params.append(menu_id)
        if order_date:
            try:
                datetime.date.fromisoformat(order_date)
            except Exception:
                return respond({"msg": "order_date must be YYYY-MM-DD"}, 400)
            fields.append("order_date=%s")
            params.append(order_date)
        if quantity is not None:
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    raise ValueError()
            except:
                return respond({"msg": "quantity must be positive integer"}, 400)
            fields.append("quantity=%s")
            params.append(quantity)

        if not fields:
            return respond({"order_id": order_id})

        params.append(order_id)
        sql = f"UPDATE orders SET {', '.join(fields)} WHERE order_id=%s"
        conn, cur = get_cursor()
        try:
            cur.execute(sql, tuple(params))
            if cur.rowcount == 0:
                return respond({"msg": "order not found"}, 404)
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return respond({"order_id": order_id})

    if request.method == "DELETE":
        conn, cur = get_cursor()
        try:
            cur.execute("DELETE FROM orders WHERE order_id=%s", (order_id,))
            if cur.rowcount == 0:
                return respond({"msg": "order not found"}, 404)
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return '', 204

# ---------------------------
# Search endpoint
# ---------------------------
@app.route("/api/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        data = request.json or {}
        q = (data.get("q") or "").strip()
    else:
        q = (request.args.get("q") or "").strip()

    if not q:
        return respond({"msg": "query parameter 'q' is required"}, 400)

    conn, cur = get_cursor()
    try:
        cur.execute("SELECT menu_id, item_name, category, price FROM menu WHERE item_name LIKE %s", (f"%{q}%",))
        results = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return respond({"results": results})

# ---------------------------
# Health check
# ---------------------------
@app.route("/", methods=["GET"])
def index():
    return respond({"msg": "Restaurant API running"}, 200)

# ---------------------------
# Run app
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
