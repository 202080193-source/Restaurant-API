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

app.config["SECRET_KEY"] = "supersecretkey"
app.config["JWT_EXP_HOURS"] = 2

# ==================================================
# DATABASE
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
# XML HELPER
# ==================================================
def to_xml(data, root_name="items"):
    root = ET.Element(root_name)
    for row in data:
        item = ET.SubElement(root, "item")
        for k, v in row.items():
            child = ET.SubElement(item, k)
            child.text = str(v)
    return ET.tostring(root, encoding="utf-8")

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
        </form>
        """

    db = get_db()
    cur = db.cursor(dictionary=True)

    username = request.form["username"]
    password = bcrypt.generate_password_hash(request.form["password"]).decode()

    cur.execute("INSERT INTO users (username, password) VALUES (%s,%s)",
                (username, password))
    db.commit()
    db.close()

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
        </form>
        """

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM users WHERE username=%s",
                (request.form["username"],))
    user = cur.fetchone()

    if not user or not bcrypt.check_password_hash(
            user["password"], request.form["password"]):
        return "<h3>Invalid credentials</h3>"

    token = jwt.encode(
        {
            "user": user["username"],
            "exp": datetime.datetime.utcnow() +
                   datetime.timedelta(hours=2)
        },
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    session["token"] = token

    return "<h3>Login Success</h3><a href='/menu'>View Menu</a>"

# ==================================================
# MENU
# ==================================================
@app.route("/menu", methods=["GET"])
@token_required
def menu():
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM menu")
    menu = cur.fetchall()
    db.close()

    if request.args.get("format") == "xml":
        return app.response_class(to_xml(menu, "menu"),
                                  mimetype="application/xml")

    html = """
    <h1>Menu</h1>
    {% for m in menu %}
    <p>{{m.food_name}} - ₱{{m.price}}</p>
    {% endfor %}
    """
    return render_template_string(html, menu=menu)

# ==================================================
# CUSTOMERS
# ==================================================
@app.route("/api/customers", methods=["GET", "POST"])
@token_required
def customers():
    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == "GET":
        cur.execute("SELECT * FROM customers")
        data = cur.fetchall()
        db.close()
        return jsonify(data)

    data = request.get_json()
    cur.execute(
        "INSERT INTO customers (name, phone) VALUES (%s,%s)",
        (data["name"], data["phone"])
    )
    db.commit()
    db.close()
    return jsonify({"message": "Customer added"}), 201

# ==================================================
# ORDERS
# ==================================================
@app.route("/api/orders", methods=["GET", "POST"])
@token_required
def orders():
    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == "GET":
        cur.execute("""
            SELECT o.order_id, c.name, m.food_name, o.quantity, o.order_date
            FROM orders o
            JOIN customers c ON o.customer_id=c.customer_id
            JOIN menu m ON o.menu_id=m.menu_id
        """)
        data = cur.fetchall()
        db.close()
        return jsonify(data)

    data = request.get_json()
    cur.execute("""
        INSERT INTO orders (customer_id, menu_id, quantity, order_date)
        VALUES (%s,%s,%s,%s)
    """, (
        data["customer_id"],
        data["menu_id"],
        data["quantity"],
        datetime.date.today()
    ))
    db.commit()
    db.close()
    return jsonify({"message": "Order created"}), 201

# ==================================================
# SEARCH
# ==================================================
@app.route("/search")
@token_required
def search():
    q = request.args.get("q", "")

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM menu WHERE food_name LIKE %s",
                (f"%{q}%",))
    results = cur.fetchall()
    db.close()

    return jsonify(results)

# ==================================================
# HOME
# ==================================================
@app.route("/")
def index():
    return """
    <h2>Restaurant API</h2>
    <a href="/login">Login</a> |
    <a href="/register">Register</a>
    """

# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    app.run(debug=True)