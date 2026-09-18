from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = "codealpha_secret_key_2026"

DATABASE = "shop.db"


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT NOT NULL,
            category TEXT NOT NULL,
            stock INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL
        )
    """)

    count = conn.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    if count == 0:

        products = [
            (
                "Wireless Headphones",
                "Premium wireless headphones with clear sound.",
                1999,
                "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600",
                "Electronics",
                20
            ),

            (
                "Smart Watch",
                "Smart watch with fitness and notification features.",
                2999,
                "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600",
                "Electronics",
                15
            ),

            (
                "Running Shoes",
                "Comfortable running shoes for everyday use.",
                2499,
                "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600",
                "Fashion",
                25
            ),

            (
                "Backpack",
                "Stylish backpack for college and travel.",
                1499,
                "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600",
                "Accessories",
                30
            ),

            (
                "Sunglasses",
                "Modern UV protection sunglasses.",
                999,
                "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=600",
                "Fashion",
                18
            ),

            (
                "Laptop",
                "Powerful laptop for study and work.",
                54999,
                "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600",
                "Electronics",
                10
            )
        ]

        conn.executemany("""
            INSERT INTO products
            (name, description, price, image, category, stock)
            VALUES (?, ?, ?, ?, ?, ?)
        """, products)

    conn.commit()
    conn.close()


# =========================
# HOME
# =========================

@app.route("/")
def home():

    conn = get_db()

    products = conn.execute(
        "SELECT * FROM products"
    ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        products=products
    )


# =========================
# PRODUCT DETAILS
# =========================

@app.route("/product/<int:product_id>")
def product(product_id):

    conn = get_db()

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    conn.close()

    if product is None:
        return "Product not found", 404

    return render_template(
        "product.html",
        product=product
    )


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = hashlib.sha256(
            password.encode()
        ).hexdigest()

        conn = get_db()

        try:

            conn.execute("""
                INSERT INTO users
                (name, email, password)
                VALUES (?, ?, ?)
            """, (
                name,
                email,
                hashed_password
            ))

            conn.commit()
            conn.close()

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            conn.close()

            return render_template(
                "register.html",
                error="Email already registered"
            )

    return render_template("register.html")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        hashed_password = hashlib.sha256(
            password.encode()
        ).hexdigest()

        conn = get_db()

        user = conn.execute("""
            SELECT * FROM users
            WHERE email = ?
            AND password = ?
        """, (
            email,
            hashed_password
        )).fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid email or password"
        )

    return render_template("login.html")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# =========================
# ADD ORDER
# =========================

@app.route("/checkout", methods=["POST"])
def checkout():

    if "user_id" not in session:

        return redirect(url_for("login"))

    cart = session.get("cart", [])

    if not cart:

        return redirect(url_for("cart"))

    conn = get_db()

    total = 0

    for item in cart:

        product = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (item["id"],)
        ).fetchone()

        if product:
            total += product["price"] * item["quantity"]

    cursor = conn.execute("""
        INSERT INTO orders
        (user_id, total, status)
        VALUES (?, ?, ?)
    """, (
        session["user_id"],
        total,
        "Pending"
    ))

    order_id = cursor.lastrowid

    for item in cart:

        conn.execute("""
            INSERT INTO order_items
            (order_id, product_id, quantity)
            VALUES (?, ?, ?)
        """, (
            order_id,
            item["id"],
            item["quantity"]
        ))

    conn.commit()
    conn.close()

    session["cart"] = []

    return render_template(
        "cart.html",
        message=f"Order #{order_id} placed successfully!",
        cart=[],
        total=0
    )


# =========================
# CART
# =========================

@app.route("/cart")
def cart():

    cart_items = session.get("cart", [])

    conn = get_db()

    products = []

    total = 0

    for item in cart_items:

        product = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (item["id"],)
        ).fetchone()

        if product:

            item_total = (
                product["price"] *
                item["quantity"]
            )

            total += item_total

            products.append({
                "product": product,
                "quantity": item["quantity"],
                "item_total": item_total
            })

    conn.close()

    return render_template(
        "cart.html",
        cart=products,
        total=total
    )


# =========================
# ADD TO CART
# =========================

@app.route("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):

    cart = session.get("cart", [])

    found = False

    for item in cart:

        if item["id"] == product_id:

            item["quantity"] += 1

            found = True

            break

    if not found:

        cart.append({
            "id": product_id,
            "quantity": 1
        })

    session["cart"] = cart

    return redirect(url_for("cart"))


# =========================
# REMOVE FROM CART
# =========================

@app.route("/remove-from-cart/<int:product_id>")
def remove_from_cart(product_id):

    cart = session.get("cart", [])

    cart = [
        item for item in cart
        if item["id"] != product_id
    ]

    session["cart"] = cart

    return redirect(url_for("cart"))


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":

    init_db()

    print("====================================")
    print("CodeAlpha E-Commerce Store")
    print("Server: http://127.0.0.1:5000")
    print("====================================")

    app.run(
        debug=True
    )
