# ==================================================
# RESTAURANT API (JSON + XML) - Modern Design
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
# FOOD EMOJI HELPER
# ==================================================
def food_emoji(name):
    name = name.lower()
    mapping = {
        "pizza": "🍕",
        "fries": "🍟",
        "steak": "🥩",
        "chicken": "🍗",
        "pasta": "🍝",
        "salad": "🥗",
        "taco": "🌮",
        "burger": "🍔"
    }
    for key in mapping:
        if key in name:
            return mapping[key]
    return "🍴"

# ==================================================
# AUTH
# ==================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return """
        <html>
        <head>
        <style>
            body { font-family: Arial; background:#f9f9f9; display:flex; justify-content:center; align-items:center; height:100vh; }
            .container { background:white; padding:30px; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1);}
            input { width:100%; padding:10px; margin:10px 0; border-radius:5px; border:1px solid #ccc;}
            button { padding:10px 20px; border:none; border-radius:5px; background:#28a745; color:white; cursor:pointer;}
            button:hover { background:#218838;}
        </style>
        </head>
        <body>
        <div class="container">
        <h2>📝 Register</h2>
        <form method="POST">
            <input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <button>Register ✅</button>
        </form>
        <p>Already have an account? <a href="/login">Login 🔑</a></p>
        </div>
        </body>
        </html>
        """
    db = get_db(); cur = db.cursor(dictionary=True)
    pw = bcrypt.generate_password_hash(request.form["password"]).decode()
    cur.execute("INSERT INTO users (username,password) VALUES (%s,%s)",
                (request.form["username"], pw))
    db.commit(); db.close()
    return "<h3>Registered ✅</h3><a href='/login'>Login 🔑</a>"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return """
        <html>
        <head>
        <style>
            body { font-family: Arial; background:#f9f9f9; display:flex; justify-content:center; align-items:center; height:100vh; }
            .container { background:white; padding:30px; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1);}
            input { width:100%; padding:10px; margin:10px 0; border-radius:5px; border:1px solid #ccc;}
            button { padding:10px 20px; border:none; border-radius:5px; background:#007bff; color:white; cursor:pointer;}
            button:hover { background:#0069d9;}
        </style>
        </head>
        <body>
        <div class="container">
        <h2>🔑 Login</h2>
        <form method="POST">
            <input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <button>Login ✅</button>
        </form>
        <p>Don't have an account? <a href="/register">Register 📝</a></p>
        </div>
        </body>
        </html>
        """
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username=%s", (request.form["username"],))
    user = cur.fetchone(); db.close()
    if not user or not bcrypt.check_password_hash(user["password"], request.form["password"]):
        return "<h3>Invalid credentials ❌</h3>"
    token = jwt.encode({
        "user": user["username"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }, app.config["SECRET_KEY"], algorithm="HS256")
    session["token"] = token
    return "<h3>Login Success ✅</h3><a href='/menu'>View Menu 🍽️</a>"

# ==================================================
# MENU (CARD STYLE)
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
<html>
<head>
<style>
body { font-family: Arial; background:#f4f4f4; padding:20px; }
h1 { text-align:center; }
.menu-container { display:flex; flex-wrap:wrap; justify-content:center; gap:20px; }
.card { background:white; border-radius:10px; padding:20px; width:200px; box-shadow:0 4px 8px rgba(0,0,0,0.1); text-align:center; transition: transform 0.2s;}
.card:hover { transform: translateY(-5px); box-shadow:0 8px 16px rgba(0,0,0,0.2);}
button { margin:5px; padding:5px 10px; border:none; border-radius:5px; cursor:pointer;}
.edit { background:#ffc107; color:white;}
.delete { background:#dc3545; color:white;}
.add { background:#28a745; color:white; margin-bottom:20px; padding:10px 20px;}
</style>
</head>
<body>
<h1>🍽️ Menu</h1>
<a href="/menu/add"><button class="add">➕ Add New Item</button></a>
<div class="menu-container">
{% for m in menu %}
<div class="card">
<h2>{{food_emoji(m.food_name)}} {{m.food_name}}</h2>
<p>₱{{m.price}}</p>
<a href="/menu/edit/{{m.menu_id}}"><button class="edit">✏️ Edit</button></a>
<form method="POST" action="/menu/delete/{{m.menu_id}}" style="display:inline;">
<button class="delete" onclick="return confirm('Delete this item?')">🗑️ Delete</button>
</form>
</div>
{% endfor %}
</div>
</body>
</html>
""", menu=data, food_emoji=food_emoji)

# ==================================================
# CRUD FOR ADD/EDIT/DELETE
# ==================================================
@app.route("/menu/add", methods=["GET", "POST"])
@token_required
def add_menu():
    if request.method == "GET":
        return """
<html>
<head>
<style>
body { font-family: Arial; display:flex; justify-content:center; align-items:center; height:100vh; background:#f4f4f4;}
.container { background:white; padding:30px; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1);}
input { width:100%; padding:10px; margin:10px 0; border-radius:5px; border:1px solid #ccc;}
button { padding:10px 20px; border:none; border-radius:5px; background:#28a745; color:white; cursor:pointer;}
button:hover { background:#218838;}
</style>
</head>
<body>
<div class="container">
<h2>➕ Add New Food 🍴</h2>
<form method="POST">
<input name="food_name" placeholder="Food name 🍕🍔🍣" required>
<input name="price" type="number" step="0.01" placeholder="Price ₱" required>
<button>Add ✅</button>
</form>
<a href="/menu">⬅️ Back to Menu</a>
</div>
</body>
</html>
"""
    db = get_db(); cur = db.cursor()
    cur.execute("INSERT INTO menu (food_name, price) VALUES (%s,%s)",
                (request.form["food_name"], request.form["price"]))
    db.commit(); db.close()
    return "<h3>🍴 Food Added!</h3><a href='/menu'>⬅️ Back to Menu</a>"

@app.route("/menu/edit/<int:id>", methods=["GET", "POST"])
@token_required
def edit_menu(id):
    db = get_db(); cur = db.cursor(dictionary=True)
    if request.method == "GET":
        cur.execute("SELECT * FROM menu WHERE menu_id=%s", (id,))
        item = cur.fetchone(); db.close()
        return f"""
<html>
<body>
<div style='font-family:Arial;text-align:center;margin-top:50px;'>
<h2>✏️ Edit Food 🍴</h2>
<form method="POST">
<input name="food_name" value="{item['food_name']}" required>
<input name="price" type="number" step="0.01" value="{item['price']}" required>
<button>Update ✅</button>
</form>
<a href='/menu'>⬅️ Back to Menu</a>
</div>
</body>
</html>
"""
    cur.execute("UPDATE menu SET food_name=%s, price=%s WHERE menu_id=%s",
                (request.form["food_name"], request.form["price"], id))
    db.commit(); db.close()
    return "<h3>✅ Food Updated!</h3><a href='/menu'>⬅️ Back to Menu</a>"

@app.route("/menu/delete/<int:id>", methods=["POST"])
@token_required
def delete_menu(id):
    db = get_db(); cur = db.cursor()
    cur.execute("DELETE FROM menu WHERE menu_id=%s", (id,))
    db.commit(); db.close()
    return "<h3>🗑️ Food Deleted!</h3><a href='/menu'>⬅️ Back to Menu</a>"

# ==================================================
# HOME
# ==================================================
@app.route("/")
def index():
    return """
<html>
<head>
<style>
body { font-family: Arial; background:#f4f4f4; text-align:center; padding-top:50px; }
a { margin: 10px; text-decoration:none; color:white; padding:10px 20px; background:#007bff; border-radius:5px;}
a:hover { background:#0056b3; }
</style>
</head>
<body>
<h1>🍴 Welcome to the Restaurant API 🍴</h1>
<a href='/login'>Login 🔑</a>
<a href='/register'>Register 📝</a>
<p>Explore our delicious menu and order your favorite dishes! 🍔🍕🍣🍦🥗</p>
</body>
</html>
"""

# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
