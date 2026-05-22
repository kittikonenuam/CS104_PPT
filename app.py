from pathlib import Path
import sqlite3
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.secret_key = "cs104-game-key-store-demo"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  username TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  pass_hash TEXT NOT NULL,
  created TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS games (
  game_id TEXT PRIMARY KEY,
  gamename TEXT NOT NULL,
  description TEXT,
  price REAL NOT NULL,
  image TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS game_keys (
  key_id TEXT PRIMARY KEY,
  game_id TEXT NOT NULL,
  game_key TEXT NOT NULL UNIQUE,
  sold INTEGER DEFAULT 0,
  sold_date TEXT,
  FOREIGN KEY (game_id) REFERENCES games(game_id)
);

CREATE TABLE IF NOT EXISTS orders (
  order_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  total_price REAL NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS order_items (
  order_item_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL,
  game_id TEXT NOT NULL,
  key_id TEXT UNIQUE,
  price REAL NOT NULL,
  FOREIGN KEY (order_id) REFERENCES orders(order_id),
  FOREIGN KEY (game_id) REFERENCES games(game_id),
  FOREIGN KEY (key_id) REFERENCES game_keys(key_id)
);

CREATE TABLE IF NOT EXISTS categories (
  category_id TEXT PRIMARY KEY,
  cat_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS game_categories (
  game_category_id TEXT PRIMARY KEY,
  game_id TEXT NOT NULL,
  category_id TEXT NOT NULL,
  FOREIGN KEY (game_id) REFERENCES games(game_id),
  FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE IF NOT EXISTS platforms (
  platform_id TEXT PRIMARY KEY,
  platform_name TEXT NOT NULL,
  on_pc INTEGER DEFAULT 0,
  on_console INTEGER DEFAULT 0,
  on_phone INTEGER DEFAULT 0,
  platform_status TEXT
);

CREATE TABLE IF NOT EXISTS game_platforms (
  game_platform_id TEXT PRIMARY KEY,
  game_id TEXT NOT NULL,
  platform_id TEXT NOT NULL,
  FOREIGN KEY (game_id) REFERENCES games(game_id),
  FOREIGN KEY (platform_id) REFERENCES platforms(platform_id)
);
"""


SEED_SQL = """
INSERT INTO users (user_id, username, email, pass_hash) VALUES
('U001', 'tee', 'tee@example.com', 'hash_tee123'),
('U002', 'mew', 'mew@example.com', 'hash_mew123'),
('U003', 'bank', 'bank@example.com', 'hash_bank123'),
('U004', 'fern', 'fern@example.com', 'hash_fern123'),
('U005', 'boss', 'boss@example.com', 'hash_boss123'),
('U006', 'mind', 'mind@example.com', 'hash_mind123'),
('U007', 'palm', 'palm@example.com', 'hash_palm123'),
('U008', 'ice', 'ice@example.com', 'hash_ice123'),
('U009', 'non', 'non@example.com', 'hash_non123'),
('U010', 'ploy', 'ploy@example.com', 'hash_ploy123'),
('U011', 'game', 'game@example.com', 'hash_game123'),
('U012', 'nice', 'nice@example.com', 'hash_nice123'),
('U013', 'beam', 'beam@example.com', 'hash_beam123'),
('U014', 'ton', 'ton@example.com', 'hash_ton123'),
('U015', 'aom', 'aom@example.com', 'hash_aom123'),
('U016', 'first', 'first@example.com', 'hash_first123'),
('U017', 'jane', 'jane@example.com', 'hash_jane123'),
('U018', 'mark', 'mark@example.com', 'hash_mark123'),
('U019', 'nut', 'nut@example.com', 'hash_nut123'),
('U020', 'win', 'win@example.com', 'hash_win123');

INSERT INTO games (game_id, gamename, description, price, image, status) VALUES
('G001', 'Elden Ring', 'Open-world action RPG game', 1790.00, 'elden_ring.jpg', 'active'),
('G002', 'Minecraft', 'Sandbox survival and building game', 890.00, 'minecraft.jpg', 'active'),
('G003', 'Cyberpunk 2077', 'Sci-fi open-world RPG game', 1590.00, 'cyberpunk2077.jpg', 'active'),
('G004', 'Stardew Valley', 'Farming and life simulation game', 315.00, 'stardew_valley.jpg', 'active'),
('G005', 'Terraria', '2D sandbox adventure game', 220.00, 'terraria.jpg', 'active'),
('G006', 'Hades', 'Roguelike action dungeon crawler', 429.00, 'hades.jpg', 'active'),
('G007', 'Red Dead Redemption 2', 'Western open-world action game', 1890.00, 'rdr2.jpg', 'active'),
('G008', 'The Witcher 3', 'Fantasy RPG adventure game', 799.00, 'witcher3.jpg', 'active'),
('G009', 'Grand Theft Auto V', 'Open-world action crime game', 999.00, 'gtav.jpg', 'active'),
('G010', 'Hollow Knight', 'Metroidvania action platformer', 315.00, 'hollow_knight.jpg', 'active');

INSERT INTO game_keys (key_id, game_id, game_key, sold, sold_date) VALUES
('K001', 'G001', 'ELDEN-AAAA-BBBB-0001', 1, '2026-05-01 10:00:00'),
('K002', 'G001', 'ELDEN-CCCC-DDDD-0002', 0, NULL),
('K003', 'G002', 'MINE-AAAA-BBBB-0003', 1, '2026-05-02 11:30:00'),
('K004', 'G002', 'MINE-CCCC-DDDD-0004', 0, NULL),
('K005', 'G003', 'CYBER-AAAA-BBBB-0005', 1, '2026-05-03 13:20:00'),
('K006', 'G003', 'CYBER-CCCC-DDDD-0006', 0, NULL),
('K007', 'G004', 'STAR-AAAA-BBBB-0007', 1, '2026-05-04 14:10:00'),
('K008', 'G004', 'STAR-CCCC-DDDD-0008', 0, NULL),
('K009', 'G005', 'TERRA-AAAA-BBBB-0009', 1, '2026-05-05 15:45:00'),
('K010', 'G005', 'TERRA-CCCC-DDDD-0010', 0, NULL),
('K011', 'G006', 'HADES-AAAA-BBBB-0011', 1, '2026-05-06 16:00:00'),
('K012', 'G006', 'HADES-CCCC-DDDD-0012', 0, NULL),
('K013', 'G007', 'RDR2-AAAA-BBBB-0013', 1, '2026-05-07 17:10:00'),
('K014', 'G007', 'RDR2-CCCC-DDDD-0014', 0, NULL),
('K015', 'G008', 'WITCHER-AAAA-BBBB-0015', 1, '2026-05-08 18:25:00'),
('K016', 'G008', 'WITCHER-CCCC-DDDD-0016', 0, NULL),
('K017', 'G009', 'GTAV-AAAA-BBBB-0017', 1, '2026-05-09 19:40:00'),
('K018', 'G009', 'GTAV-CCCC-DDDD-0018', 0, NULL),
('K019', 'G010', 'HOLLOW-AAAA-BBBB-0019', 1, '2026-05-10 20:15:00'),
('K020', 'G010', 'HOLLOW-CCCC-DDDD-0020', 0, NULL);

INSERT INTO categories (category_id, cat_name) VALUES
('C001', 'Action'),
('C002', 'Adventure'),
('C003', 'RPG'),
('C004', 'Sandbox'),
('C005', 'Simulation'),
('C006', 'Survival'),
('C007', 'Indie'),
('C008', 'Open World'),
('C009', 'Platformer'),
('C010', 'Roguelike');

INSERT INTO platforms (platform_id, platform_name, on_pc, on_console, on_phone, platform_status) VALUES
('P001', 'Steam', 1, 0, 0, 'active'),
('P002', 'Epic Games', 1, 0, 0, 'active'),
('P003', 'GOG', 1, 0, 0, 'active'),
('P004', 'Xbox', 0, 1, 0, 'active'),
('P005', 'PlayStation', 0, 1, 0, 'active'),
('P006', 'Nintendo Switch', 0, 1, 0, 'active'),
('P007', 'Microsoft Store', 1, 1, 0, 'active'),
('P008', 'Android', 0, 0, 1, 'active'),
('P009', 'iOS', 0, 0, 1, 'active'),
('P010', 'Battle.net', 1, 0, 0, 'active');

INSERT INTO orders (order_id, user_id, total_price) VALUES
('O001', 'U001', 1790.00),
('O002', 'U002', 890.00),
('O003', 'U003', 1590.00),
('O004', 'U004', 315.00),
('O005', 'U005', 220.00),
('O006', 'U006', 429.00),
('O007', 'U007', 1890.00),
('O008', 'U008', 799.00),
('O009', 'U009', 999.00),
('O010', 'U010', 315.00);

INSERT INTO order_items (order_item_id, order_id, game_id, key_id, price) VALUES
('OI001', 'O001', 'G001', 'K001', 1790.00),
('OI002', 'O002', 'G002', 'K003', 890.00),
('OI003', 'O003', 'G003', 'K005', 1590.00),
('OI004', 'O004', 'G004', 'K007', 315.00),
('OI005', 'O005', 'G005', 'K009', 220.00),
('OI006', 'O006', 'G006', 'K011', 429.00),
('OI007', 'O007', 'G007', 'K013', 1890.00),
('OI008', 'O008', 'G008', 'K015', 799.00),
('OI009', 'O009', 'G009', 'K017', 999.00),
('OI010', 'O010', 'G010', 'K019', 315.00);

INSERT INTO game_categories (game_category_id, game_id, category_id) VALUES
('GC001', 'G001', 'C003'),
('GC002', 'G002', 'C004'),
('GC003', 'G003', 'C003'),
('GC004', 'G004', 'C005'),
('GC005', 'G005', 'C006'),
('GC006', 'G006', 'C010'),
('GC007', 'G007', 'C008'),
('GC008', 'G008', 'C003'),
('GC009', 'G009', 'C001'),
('GC010', 'G010', 'C009');

INSERT INTO game_platforms (game_platform_id, game_id, platform_id) VALUES
('GP001', 'G001', 'P001'),
('GP002', 'G002', 'P007'),
('GP003', 'G003', 'P002'),
('GP004', 'G004', 'P001'),
('GP005', 'G005', 'P003'),
('GP006', 'G006', 'P001'),
('GP007', 'G007', 'P005'),
('GP008', 'G008', 'P003'),
('GP009', 'G009', 'P002'),
('GP010', 'G010', 'P006');
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count == 0:
            conn.executescript(SEED_SQL)
            seed_rich_game_keys(conn)


def reset_demo_data():
    with get_db() as conn:
        conn.executescript(
            """
            DELETE FROM game_platforms;
            DELETE FROM game_categories;
            DELETE FROM order_items;
            DELETE FROM orders;
            DELETE FROM game_keys;
            DELETE FROM platforms;
            DELETE FROM categories;
            DELETE FROM games;
            DELETE FROM users;
            """
        )
        conn.executescript(SEED_SQL)
        seed_rich_game_keys(conn)


def seed_rich_game_keys(conn):
    key_plan = {
        "G001": ("ELDEN", 0),
        "G002": ("MINE", 8),
        "G003": ("CYBER", 6),
        "G004": ("STAR", 10),
        "G005": ("TERRA", 7),
        "G006": ("HADES", 9),
        "G007": ("RDR2", 5),
        "G008": ("WITCHER", 8),
        "G009": ("GTAV", 6),
        "G010": ("HOLLOW", 0),
    }
    existing_orders = {
        "G001": "K001",
        "G002": "K003",
        "G003": "K005",
        "G004": "K007",
        "G005": "K009",
        "G006": "K011",
        "G007": "K013",
        "G008": "K015",
        "G009": "K017",
        "G010": "K019",
    }

    for game_id, (prefix, available_count) in key_plan.items():
        sold_count = 10 - available_count
        existing_key_id = existing_orders[game_id]
        conn.execute(
            "UPDATE game_keys SET sold = 1, sold_date = COALESCE(sold_date, '2026-05-11 10:00:00') WHERE game_id = ?",
            (game_id,),
        )
        conn.execute(
            "UPDATE game_keys SET sold = 1, sold_date = COALESCE(sold_date, '2026-05-11 10:00:00') WHERE key_id = ?",
            (existing_key_id,),
        )
        for number in range(1, 11):
            key_id = f"{game_id.replace('G', 'K')}-{number:02d}"
            if conn.execute("SELECT 1 FROM game_keys WHERE key_id = ?", (key_id,)).fetchone():
                continue
            sold = 1 if number <= sold_count else 0
            sold_date = f"2026-05-{10 + number:02d} 12:00:00" if sold else None
            conn.execute(
                """
                INSERT INTO game_keys (key_id, game_id, game_key, sold, sold_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    key_id,
                    game_id,
                    f"{prefix}-MOCK-STOCK-{number:04d}",
                    sold,
                    sold_date,
                ),
            )


def fetch_one(query, params=()):
    with get_db() as conn:
        return conn.execute(query, params).fetchone()


def fetch_all(query, params=()):
    with get_db() as conn:
        return conn.execute(query, params).fetchall()


def next_id(prefix, table, column):
    row = fetch_one(
        f"SELECT {column} FROM {table} WHERE {column} LIKE ? "
        f"ORDER BY CAST(SUBSTR({column}, ?) AS INTEGER) DESC LIMIT 1",
        (f"{prefix}%", len(prefix) + 1),
    )
    if not row:
        return f"{prefix}001"
    current = int(row[column].replace(prefix, ""))
    return f"{prefix}{current + 1:03d}"


def next_id_conn(conn, prefix, table, column):
    row = conn.execute(
        f"SELECT {column} FROM {table} WHERE {column} LIKE ? "
        f"ORDER BY CAST(SUBSTR({column}, ?) AS INTEGER) DESC LIMIT 1",
        (f"{prefix}%", len(prefix) + 1),
    ).fetchone()
    if not row:
        return f"{prefix}001"
    current = int(row[column].replace(prefix, ""))
    return f"{prefix}{current + 1:03d}"


def increment_code(code, prefix, amount):
    current = int(code.replace(prefix, ""))
    return f"{prefix}{current + amount:03d}"


def save_game_image(file_storage, game_id):
    if not file_storage or not file_storage.filename:
        return None

    extension = file_storage.filename.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        flash("Image upload must be png, jpg, jpeg, gif, or webp.")
        return None

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = secure_filename(file_storage.filename)
    filename = f"{game_id}_{safe_name}"
    file_storage.save(UPLOAD_DIR / filename)
    return f"uploads/{filename}"


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Please login as admin first.")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_auth_state():
    cart = session.get("cart", {})
    return {
        "is_admin": session.get("is_admin", False),
        "cart_count": sum(cart.values()) if isinstance(cart, dict) else 0,
    }


def get_cart():
    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}
    return cart


def cart_rows():
    cart = get_cart()
    if not cart:
        return []
    placeholders = ",".join("?" for _ in cart)
    rows = catalog_query(f"WHERE g.game_id IN ({placeholders})", tuple(cart.keys()))
    return [
        {
            "game": row,
            "quantity": cart[row["game_id"]],
            "line_total": row["price"] * cart[row["game_id"]],
        }
        for row in rows
    ]


def catalog_query(where="", params=()):
    return fetch_all(
        f"""
        SELECT
          g.game_id,
          g.gamename,
          g.description,
          g.price,
          g.image,
          g.status,
          COALESCE(c.cat_name, '-') AS category,
          COALESCE(p.platform_name, '-') AS platform,
          SUM(CASE WHEN k.sold = 0 THEN 1 ELSE 0 END) AS available_keys,
          COUNT(k.key_id) AS total_keys
        FROM games AS g
        LEFT JOIN game_categories AS gc ON g.game_id = gc.game_id
        LEFT JOIN categories AS c ON gc.category_id = c.category_id
        LEFT JOIN game_platforms AS gp ON g.game_id = gp.game_id
        LEFT JOIN platforms AS p ON gp.platform_id = p.platform_id
        LEFT JOIN game_keys AS k ON g.game_id = k.game_id
        {where}
        GROUP BY g.game_id
        ORDER BY g.game_id;
        """,
        params,
    )


@app.before_request
def ensure_database():
    init_db()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["is_admin"] = True
            flash("Admin login successful.")
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Wrong username or password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("store"))


@app.route("/")
def store():
    search = request.args.get("q", "").strip()
    category_id = request.args.get("category", "").strip()
    platform_id = request.args.get("platform", "").strip()
    clauses = ["g.status = 'active'"]
    params = []
    if search:
        clauses.append("(g.gamename LIKE ? OR g.description LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if category_id:
        clauses.append("gc.category_id = ?")
        params.append(category_id)
    if platform_id:
        clauses.append("gp.platform_id = ?")
        params.append(platform_id)

    games = catalog_query("WHERE " + " AND ".join(clauses), params)
    categories = fetch_all("SELECT * FROM categories ORDER BY cat_name")
    platforms = fetch_all("SELECT * FROM platforms WHERE platform_status = 'active' ORDER BY platform_name")
    featured = games[:3]
    return render_template(
        "store.html",
        games=games,
        featured=featured,
        categories=categories,
        platforms=platforms,
        search=search,
        category_id=category_id,
        platform_id=platform_id,
    )


@app.route("/store/<game_id>")
def game_detail(game_id):
    game = catalog_query("WHERE g.game_id = ?", (game_id,))
    if not game:
        flash("Game not found.")
        return redirect(url_for("store"))
    users = fetch_all("SELECT user_id, username, email FROM users ORDER BY user_id")
    keys = fetch_all(
        """
        SELECT key_id, sold, sold_date
        FROM game_keys
        WHERE game_id = ?
        ORDER BY key_id
        """,
        (game_id,),
    )
    return render_template("game_detail.html", game=game[0], users=users, keys=keys)


@app.route("/cart")
def cart():
    rows = cart_rows()
    users = fetch_all("SELECT user_id, username, email FROM users ORDER BY user_id")
    total = sum(row["line_total"] for row in rows)
    return render_template("cart.html", rows=rows, users=users, total=total)


@app.route("/cart/add/<game_id>", methods=["POST"])
def add_to_cart(game_id):
    game = catalog_query("WHERE g.game_id = ? AND g.status = 'active'", (game_id,))
    if not game:
        flash("Game not found.")
        return redirect(url_for("store"))
    game = game[0]
    cart = get_cart()
    current_quantity = int(cart.get(game_id, 0))
    if current_quantity >= game["available_keys"]:
        flash("Not enough available keys for this game.")
        return redirect(request.referrer or url_for("game_detail", game_id=game_id))
    cart[game_id] = current_quantity + 1
    session["cart"] = cart
    session.modified = True
    flash(f"Added {game['gamename']} to cart.")
    return redirect(request.form.get("next") or request.referrer or url_for("cart"))


@app.route("/cart/remove/<game_id>", methods=["POST"])
def remove_from_cart(game_id):
    cart = get_cart()
    cart.pop(game_id, None)
    session["cart"] = cart
    session.modified = True
    flash("Removed item from cart.")
    return redirect(url_for("cart"))


@app.route("/cart/clear", methods=["POST"])
def clear_cart():
    session["cart"] = {}
    session.modified = True
    flash("Cart cleared.")
    return redirect(url_for("cart"))


@app.route("/cart/checkout", methods=["POST"])
def checkout_cart():
    cart = get_cart()
    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for("cart"))

    user_id = request.form["user_id"]
    with get_db() as conn:
        order_id = next_id_conn(conn, "O", "orders", "order_id")
        order_item_id = next_id_conn(conn, "OI", "order_items", "order_item_id")
        total_price = 0
        selected_items = []

        for game_id, quantity in cart.items():
            game = conn.execute("SELECT * FROM games WHERE game_id = ?", (game_id,)).fetchone()
            if not game:
                flash("One cart item no longer exists.")
                return redirect(url_for("cart"))
            keys = conn.execute(
                """
                SELECT * FROM game_keys
                WHERE game_id = ? AND sold = 0
                ORDER BY key_id
                LIMIT ?
                """,
                (game_id, quantity),
            ).fetchall()
            if len(keys) < quantity:
                flash(f"Not enough stock for {game['gamename']}.")
                return redirect(url_for("cart"))
            for key in keys:
                selected_items.append((game, key))
                total_price += game["price"]

        conn.execute(
            "INSERT INTO orders (order_id, user_id, total_price) VALUES (?, ?, ?)",
            (order_id, user_id, total_price),
        )
        for index, (game, key) in enumerate(selected_items):
            current_order_item_id = increment_code(order_item_id, "OI", index)
            conn.execute(
                """
                INSERT INTO order_items (order_item_id, order_id, game_id, key_id, price)
                VALUES (?, ?, ?, ?, ?)
                """,
                (current_order_item_id, order_id, game["game_id"], key["key_id"], game["price"]),
            )
            conn.execute(
                "UPDATE game_keys SET sold = 1, sold_date = CURRENT_TIMESTAMP WHERE key_id = ?",
                (key["key_id"],),
            )

    session["cart"] = {}
    session.modified = True
    return redirect(url_for("receipt", order_id=order_id))


@app.route("/checkout/<game_id>", methods=["POST"])
def checkout(game_id):
    user_id = request.form["user_id"]
    with get_db() as conn:
        game = conn.execute("SELECT * FROM games WHERE game_id = ?", (game_id,)).fetchone()
        if not game:
            flash("Game not found.")
            return redirect(url_for("store"))

        key = conn.execute(
            """
            SELECT * FROM game_keys
            WHERE game_id = ? AND sold = 0
            ORDER BY key_id
            LIMIT 1
            """,
            (game_id,),
        ).fetchone()
        if not key:
            flash("This game is out of stock.")
            return redirect(url_for("game_detail", game_id=game_id))

        order_id = next_id("O", "orders", "order_id")
        order_item_id = next_id("OI", "order_items", "order_item_id")
        conn.execute(
            "INSERT INTO orders (order_id, user_id, total_price) VALUES (?, ?, ?)",
            (order_id, user_id, game["price"]),
        )
        conn.execute(
            """
            INSERT INTO order_items (order_item_id, order_id, game_id, key_id, price)
            VALUES (?, ?, ?, ?, ?)
            """,
            (order_item_id, order_id, game_id, key["key_id"], game["price"]),
        )
        conn.execute(
            "UPDATE game_keys SET sold = 1, sold_date = CURRENT_TIMESTAMP WHERE key_id = ?",
            (key["key_id"],),
        )
    return redirect(url_for("receipt", order_id=order_id))


@app.route("/receipt/<order_id>")
def receipt(order_id):
    order = fetch_one(
        """
        SELECT o.order_id, o.total_price, u.username, u.email
        FROM orders AS o
        JOIN users AS u ON o.user_id = u.user_id
        WHERE o.order_id = ?
        """,
        (order_id,),
    )
    if not order:
        flash("Receipt not found.")
        return redirect(url_for("store"))
    items = fetch_all(
        """
        SELECT g.gamename, oi.price, k.game_key
        FROM order_items AS oi
        JOIN games AS g ON oi.game_id = g.game_id
        JOIN game_keys AS k ON oi.key_id = k.key_id
        WHERE oi.order_id = ?
        ORDER BY oi.order_item_id
        """,
        (order_id,),
    )
    return render_template("receipt.html", order=order, items=items)


@app.route("/dashboard")
@admin_required
def dashboard():
    stats = {
        "games": fetch_one("SELECT COUNT(*) AS count FROM games")["count"],
        "users": fetch_one("SELECT COUNT(*) AS count FROM users")["count"],
        "orders": fetch_one("SELECT COUNT(*) AS count FROM orders")["count"],
        "revenue": fetch_one("SELECT COALESCE(SUM(total_price), 0) AS total FROM orders")["total"],
    }
    games = catalog_query()
    recent_orders = fetch_all(
        """
        SELECT o.order_id, u.username, g.gamename, oi.price, k.game_key
        FROM orders AS o
        JOIN users AS u ON o.user_id = u.user_id
        JOIN order_items AS oi ON o.order_id = oi.order_id
        JOIN games AS g ON oi.game_id = g.game_id
        JOIN game_keys AS k ON oi.key_id = k.key_id
        ORDER BY o.order_id DESC
        LIMIT 5;
        """
    )
    return render_template("dashboard.html", stats=stats, games=games, recent_orders=recent_orders)


@app.route("/reset-demo", methods=["POST"])
@admin_required
def reset_demo():
    reset_demo_data()
    flash("Demo data has been reset to the original 10 games, 20 users, and sample orders.")
    return redirect(url_for("dashboard"))


@app.route("/games")
@admin_required
def games():
    rows = fetch_all("SELECT * FROM games ORDER BY game_id")
    return render_template("games.html", games=rows)


@app.route("/games/new", methods=["GET", "POST"])
@admin_required
def new_game():
    if request.method == "POST":
        game_id = next_id("G", "games", "game_id")
        image_path = save_game_image(request.files.get("image_file"), game_id)
        if not image_path:
            image_path = request.form.get("image", "").strip()
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO games (game_id, gamename, description, price, image, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    request.form["gamename"].strip(),
                    request.form.get("description", "").strip(),
                    float(request.form["price"]),
                    image_path,
                    request.form.get("status", "active").strip(),
                ),
            )
        flash(f"Created game {game_id}.")
        return redirect(url_for("games"))
    return render_template("game_form.html", game=None, title="Add Game")


@app.route("/games/<game_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_game(game_id):
    game = fetch_one("SELECT * FROM games WHERE game_id = ?", (game_id,))
    if not game:
        flash("Game not found.")
        return redirect(url_for("games"))

    if request.method == "POST":
        image_path = save_game_image(request.files.get("image_file"), game_id)
        if not image_path:
            image_path = request.form.get("image", "").strip()
        with get_db() as conn:
            conn.execute(
                """
                UPDATE games
                SET gamename = ?, description = ?, price = ?, image = ?, status = ?
                WHERE game_id = ?
                """,
                (
                    request.form["gamename"].strip(),
                    request.form.get("description", "").strip(),
                    float(request.form["price"]),
                    image_path,
                    request.form.get("status", "active").strip(),
                    game_id,
                ),
            )
        flash(f"Updated game {game_id}.")
        return redirect(url_for("games"))
    return render_template("game_form.html", game=game, title="Edit Game")


@app.route("/games/<game_id>/delete", methods=["POST"])
@admin_required
def delete_game(game_id):
    references = fetch_one(
        """
        SELECT
          (SELECT COUNT(*) FROM game_keys WHERE game_id = ?) +
          (SELECT COUNT(*) FROM order_items WHERE game_id = ?) +
          (SELECT COUNT(*) FROM game_categories WHERE game_id = ?) +
          (SELECT COUNT(*) FROM game_platforms WHERE game_id = ?) AS total
        """,
        (game_id, game_id, game_id, game_id),
    )["total"]
    if references:
        flash("This game is connected to keys, orders, categories, or platforms. Edit it instead, or delete a newly-created demo game.")
        return redirect(url_for("games"))

    with get_db() as conn:
        conn.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
    flash(f"Deleted game {game_id}.")
    return redirect(url_for("games"))


@app.route("/keys")
@admin_required
def keys():
    rows = fetch_all(
        """
        SELECT k.*, g.gamename
        FROM game_keys AS k
        JOIN games AS g ON k.game_id = g.game_id
        ORDER BY k.key_id
        """
    )
    return render_template("keys.html", keys=rows)


@app.route("/orders")
@admin_required
def orders():
    rows = fetch_all(
        """
        SELECT o.order_id, u.username, g.gamename, oi.price, k.game_key
        FROM orders AS o
        JOIN users AS u ON o.user_id = u.user_id
        JOIN order_items AS oi ON o.order_id = oi.order_id
        JOIN games AS g ON oi.game_id = g.game_id
        JOIN game_keys AS k ON oi.key_id = k.key_id
        ORDER BY o.order_id
        """
    )
    return render_template("orders.html", orders=rows)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
