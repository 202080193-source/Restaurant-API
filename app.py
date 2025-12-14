# ==================================================
# RESTAURANT API (JSON + XML)
# Flask + MySQL + JWT + Session
# ==================================================

from flask import Flask, request, jsonify, render_template_string, session
from flask_bcrypt import Bcrypt
from functools import wraps
import datetime
import jwt
import mysql.connector
import xml.etree.ElementTree as ET

# ==================================================
# APP SETUP
# ==================================================
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config.update(SECRET_KEY="supersecretkey", JWT_EXP_HOURS=2)

# ==================================================
# DATABASE CONFIG
# ==================================================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "AdventureTime514!",
    "database": "restaurand_db"
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# ==================================================
# DB INIT
# ==================================================

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) UNIQUE,
        password VARCHAR(255)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS menu (
        menu_id INT AUTO_INCREMENT PRIMARY KEY,
        food_name VARCHAR(100),
        price DECIMAL(10,2)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100),
        phone VARCHAR(20)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INT AUTO_INCREMENT PRIMARY KEY,
        customer_id INT,
        menu_id INT,
        quantity INT,
        order_date DATE,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY (menu_id) REFERENCES menu(menu_id)
    )""")
    db.commit(); db.close()

# ==================================================
# XML + RESPONSE HELPER
# ==================================================

def to_xml(data, root_name="items"):
    root = ET.Element(root_name)
    for row in data:
        item = ET.SubElement(root, "item")
        for k, v in row.items():
            ET.SubElement(item, k).text = str(v)
    return ET.tostring(root, encoding="utf-8")


def respond(data, root="items"):
    fmt = request.args.get("format")
    accept = request.headers.get("Accept", "")

    if fmt == "xml" or "application/xml" in accept:
        return app.response_class(to_xml(data, root), mimetype="application/xml")
    return jsonify(data)

# ==================================================
# JWT DECORATOR
# ==================================================

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token.replace("Bearer ", "")
        else:
            token = session.get("token")
        if not token:
            return jsonify({"error": "Token missing"}), 401
        try:
            jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except:
            return jsonify({"error": "Invalid or expired token"}), 401
        return f(*args, **kwargs)
    return decorated

# ==================================================
# AUTH
# ==================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return """
        <h1>Register</h1>
        <form method="POST">
            <input name="username" required><br><br>
            <input name="password" type="password" required><br><br>
            <button>Register</button>
        </form>"""

    db = get_db(); cur = db.cursor(dictionary=True)
    pw = bcrypt.generate_password_hash(request.form["password"]).decode()
    cur.execute("INSERT INTO users (username,password) VALUES (%s,%s)",
                (request.form["username"], pw))
    db.commit(); db.close()
    return "<h3>Registered</h3><a href='/login'>Login</a>"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return """
        <h1>Login</h1>
        <form method="POST">
            <input name="username" required><br><br>
            <input name="password" type="password" required><br><br>
            <button>Login</button>
        </form>"""

    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username=%s", (request.form["username"],))
    user = cur.fetchone(); db.close()

    if not user or not bcrypt.check_password_hash(user["password"], request.form["password"]):
        return "<h3>Invalid credentials</h3>"

    token = jwt.encode({
        "user": user["username"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }, app.config["SECRET_KEY"], algorithm="HS256")

    session["token"] = token
    return "<h3>Login Success</h3><a href='/menu'>View Menu</a>"

# ==================================================
# MENU (HTML + JSON + XML)
# ==================================================
@app.route("/menu")
@token_required
def menu():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM menu")
    data = cur.fetchall(); db.close()

    if request.args.get("format") or "application/json" in request.headers.get("Accept", ""):
        return respond(data, "menu")

    return render_template_string("""
<h1>Menu</h1>
<a href="/menu/add">➕ Add Item</a>
<hr>
{% for m in menu %}
<p>
<b>{{m.food_name}}</b> - ₱{{m.price}}
<a href="/menu/edit/{{m.menu_id}}">✏ Edit</a>
<form method="POST" action="/menu/delete/{{m.menu_id}}" style="display:inline;">
    <button onclick="return confirm('Delete item?')">🗑 Delete</button>
</form>
</p>
{% endfor %}
""", menu=data)


# ==================================================
# CUSTOMERS (JSON + XML)
# ==================================================
@app.route("/api/customers", methods=["GET", "POST"])
@token_required
def customers():
    db = get_db(); cur = db.cursor(dictionary=True)

    if request.method == "GET":
        cur.execute("SELECT * FROM customers")
        data = cur.fetchall(); db.close()
        return respond(data, "customers")

    data = request.get_json()
    cur.execute("INSERT INTO customers (name,phone) VALUES (%s,%s)",
                (data["name"], data["phone"]))
    db.commit(); db.close()
    return respond([{ "message": "Customer added" }])

# ==================================================
# ORDERS (JSON + XML)
# ==================================================
@app.route("/api/orders", methods=["GET", "POST"])
@token_required
def orders():
    db = get_db(); cur = db.cursor(dictionary=True)

    if request.method == "GET":
        cur.execute("""
        SELECT o.order_id, c.name, m.food_name, o.quantity, o.order_date
        FROM orders o
        JOIN customers c ON o.customer_id=c.customer_id
        JOIN menu m ON o.menu_id=m.menu_id
        """)
        data = cur.fetchall(); db.close()
        return respond(data, "orders")

    data = request.get_json()
    cur.execute("""
        INSERT INTO orders (customer_id,menu_id,quantity,order_date)
        VALUES (%s,%s,%s,%s)
    """, (data["customer_id"], data["menu_id"], data["quantity"], datetime.date.today()))
    db.commit(); db.close()
    return respond([{ "message": "Order created" }])

# ==================================================
# SEARCH (JSON + XML)
# ==================================================
@app.route("/search")
@token_required
def search():
    q = request.args.get("q", "")
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM menu WHERE food_name LIKE %s", (f"%{q}%",))
    data = cur.fetchall(); db.close()
    return respond(data, "results")

#===================================================
# CRUD IN BROWSER 
# ==================================================
@app.route("/menu/add", methods=["GET", "POST"])
@token_required
def add_menu():
    if request.method == "GET":
        return """
        <h2>Add Menu Item</h2>
        <form method="POST">
            <input name="food_name" placeholder="Food name" required><br><br>
            <input name="price" type="number" step="0.01" placeholder="Price" required><br><br>
            <button>Add</button>
        </form>
        <a href="/menu">Back</a>
        """

    db = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO menu (food_name, price) VALUES (%s,%s)",
        (request.form["food_name"], request.form["price"])
    )
    db.commit()
    db.close()

    return "<h3>Menu added</h3><a href='/menu'>View Menu</a>"

@app.route("/menu/edit/<int:id>", methods=["GET", "POST"])
@token_required
def edit_menu(id):
    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == "GET":
        cur.execute("SELECT * FROM menu WHERE menu_id=%s", (id,))
        item = cur.fetchone()
        db.close()

        return f"""
        <h2>Edit Menu</h2>
        <form method="POST">
            <input name="food_name" value="{item['food_name']}" required><br><br>
            <input name="price" type="number" step="0.01" value="{item['price']}" required><br><br>
            <button>Update</button>
        </form>
        """

    cur.execute(
        "UPDATE menu SET food_name=%s, price=%s WHERE menu_id=%s",
        (request.form["food_name"], request.form["price"], id)
    )
    db.commit()
    db.close()

    return "<h3>Updated</h3><a href='/menu'>Back</a>"

@app.route("/menu/delete/<int:id>", methods=["POST"])
@token_required
def delete_menu(id):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM menu WHERE menu_id=%s", (id,))
    db.commit()
    db.close()
    return "<h3>Deleted</h3><a href='/menu'>Back</a>"


# ==================================================
# HOME
# ==================================================
@app.route("/")
def index():
    return """
    <h2>Restaurant API</h2>
    <a href='/login'>Login</a> |
    <a href='/register'>Register</a>
    """

# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
