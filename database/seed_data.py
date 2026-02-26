"""Generate realistic e-commerce demo data for the Enterprise AI Assistant."""

import sqlite3
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

from logger.logging import get_logger

logger = get_logger(__name__)

# Product catalog data
CATEGORIES = {
    "Electronics": {
        "subcategories": ["Smartphones", "Laptops", "Headphones", "Tablets", "Cameras"],
        "brands": ["TechPro", "NovaTech", "DigitalEdge", "SmartLine", "PixelCore"],
        "price_range": (49.99, 1999.99),
        "cost_ratio": (0.4, 0.6),
    },
    "Clothing": {
        "subcategories": ["T-Shirts", "Jeans", "Jackets", "Dresses", "Shoes"],
        "brands": ["UrbanStyle", "ClassicWear", "TrendSet", "ActiveFit", "EcoThread"],
        "price_range": (19.99, 299.99),
        "cost_ratio": (0.3, 0.5),
    },
    "Home & Kitchen": {
        "subcategories": ["Cookware", "Furniture", "Decor", "Appliances", "Bedding"],
        "brands": ["HomeEssentials", "CozyLiving", "KitchenPro", "ModernNest", "PureLiving"],
        "price_range": (14.99, 899.99),
        "cost_ratio": (0.35, 0.55),
    },
    "Books": {
        "subcategories": ["Fiction", "Non-Fiction", "Technical", "Self-Help", "Children"],
        "brands": ["PageTurner", "MindGrowth", "TechReads", "StoryHouse", "KidsWorld"],
        "price_range": (7.99, 59.99),
        "cost_ratio": (0.2, 0.4),
    },
    "Sports": {
        "subcategories": ["Fitness", "Outdoor", "Team Sports", "Yoga", "Running"],
        "brands": ["FitGear", "TrailBlazer", "ProSport", "ZenFlex", "SpeedRun"],
        "price_range": (9.99, 499.99),
        "cost_ratio": (0.3, 0.5),
    },
    "Beauty": {
        "subcategories": ["Skincare", "Makeup", "Haircare", "Fragrance", "Wellness"],
        "brands": ["GlowUp", "PureSkin", "LuxBeauty", "NatureGlow", "VitalCare"],
        "price_range": (5.99, 199.99),
        "cost_ratio": (0.15, 0.35),
    },
    "Toys": {
        "subcategories": ["Educational", "Action Figures", "Board Games", "Building Sets", "Dolls"],
        "brands": ["FunLearn", "HeroWorld", "GameMaster", "BuildIt", "DreamPlay"],
        "price_range": (9.99, 149.99),
        "cost_ratio": (0.25, 0.45),
    },
    "Office": {
        "subcategories": ["Supplies", "Furniture", "Technology", "Organization", "Writing"],
        "brands": ["WorkSmart", "DeskPro", "OfficeTech", "NeatSpace", "PenCraft"],
        "price_range": (4.99, 599.99),
        "cost_ratio": (0.3, 0.5),
    },
    "Garden": {
        "subcategories": ["Tools", "Plants", "Outdoor Furniture", "Lighting", "Irrigation"],
        "brands": ["GreenThumb", "GardenPro", "OutdoorLife", "SunGlow", "AquaGrow"],
        "price_range": (7.99, 399.99),
        "cost_ratio": (0.3, 0.5),
    },
    "Automotive": {
        "subcategories": ["Accessories", "Parts", "Tools", "Electronics", "Care"],
        "brands": ["AutoPro", "DriveMax", "MechTools", "CarTech", "ShineGuard"],
        "price_range": (9.99, 499.99),
        "cost_ratio": (0.35, 0.55),
    },
}

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Carol", "Kevin", "Amanda", "Brian", "Dorothy", "George", "Melissa",
    "Timothy", "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna", "Stephen", "Brenda",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter",
]

CITIES = [
    ("New York", "NY"), ("Los Angeles", "CA"), ("Chicago", "IL"), ("Houston", "TX"),
    ("Phoenix", "AZ"), ("Philadelphia", "PA"), ("San Antonio", "TX"), ("San Diego", "CA"),
    ("Dallas", "TX"), ("San Jose", "CA"), ("Austin", "TX"), ("Jacksonville", "FL"),
    ("Fort Worth", "TX"), ("Columbus", "OH"), ("Charlotte", "NC"), ("San Francisco", "CA"),
    ("Indianapolis", "IN"), ("Seattle", "WA"), ("Denver", "CO"), ("Nashville", "TN"),
    ("Portland", "OR"), ("Boston", "MA"), ("Atlanta", "GA"), ("Miami", "FL"),
    ("Minneapolis", "MN"), ("Detroit", "MI"), ("Tampa", "FL"), ("Pittsburgh", "PA"),
]

REVIEW_TITLES_POSITIVE = [
    "Excellent product!", "Highly recommend!", "Best purchase ever",
    "Great value for money", "Exceeded expectations", "Love it!",
    "Perfect for my needs", "Outstanding quality", "Would buy again",
    "Fantastic!", "Very satisfied", "Top notch",
]

REVIEW_TITLES_NEGATIVE = [
    "Disappointed", "Not as expected", "Poor quality",
    "Would not recommend", "Broke after a week", "Waste of money",
    "Terrible experience", "Not worth it", "Very dissatisfied",
]

REVIEW_BODIES_POSITIVE = [
    "This product exceeded my expectations in every way. The build quality is excellent and it works perfectly.",
    "I've been using this for a few weeks now and I'm very happy with my purchase. Highly recommended!",
    "Great product at a fair price. Shipping was fast and packaging was secure.",
    "Exactly what I was looking for. The quality is impressive for this price point.",
    "This is my second purchase of this product. That should tell you how good it is!",
    "Bought this as a gift and the recipient loved it. Will definitely buy from this brand again.",
]

REVIEW_BODIES_NEGATIVE = [
    "The product arrived damaged and customer support was unhelpful. Very disappointed.",
    "Quality is much lower than what was advertised. The materials feel cheap.",
    "Stopped working after just two weeks of normal use. Not worth the money.",
    "The product looks nothing like the pictures. I'm returning this.",
]


def generate_tracking_number():
    """Generate a realistic tracking number."""
    prefix = random.choice(["1Z", "94", "92", "JD"])
    digits = ''.join(random.choices(string.digits, k=12))
    return f"{prefix}{digits}"


def seed_database(db_path: str = "database/ecommerce.db"):
    """Seed the database with realistic e-commerce data."""
    random.seed(42)  # Reproducibility

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Read and execute schema
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.executescript(schema_sql)

    logger.info("Schema created, seeding data...")

    # --- Customers (500) ---
    customers = []
    used_emails = set()
    segments = ["Consumer", "Corporate", "Enterprise"]
    segment_weights = [0.6, 0.3, 0.1]

    for i in range(500):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)

        # Ensure unique email
        base_email = f"{first.lower()}.{last.lower()}"
        email = f"{base_email}@example.com"
        suffix = 1
        while email in used_emails:
            email = f"{base_email}{suffix}@example.com"
            suffix += 1
        used_emails.add(email)

        city, state = random.choice(CITIES)
        segment = random.choices(segments, weights=segment_weights, k=1)[0]
        zip_code = f"{random.randint(10000, 99999)}"
        phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
        address = f"{random.randint(1, 9999)} {random.choice(['Main', 'Oak', 'Elm', 'Park', 'Cedar', 'Maple', 'Pine', 'Lake', 'Hill', 'River'])} {random.choice(['St', 'Ave', 'Blvd', 'Dr', 'Ln', 'Rd'])}"

        # Random creation date in the last 2 years
        days_ago = random.randint(1, 730)
        created_at = datetime.now() - timedelta(days=days_ago)

        customers.append((
            first, last, email, phone, address, city, state, zip_code,
            "US", segment, 0, created_at.strftime("%Y-%m-%d %H:%M:%S")
        ))

    cursor.executemany(
        "INSERT INTO customers (first_name, last_name, email, phone, address, city, state, zip_code, country, segment, lifetime_value, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        customers
    )
    logger.info(f"Inserted {len(customers)} customers")

    # --- Products (200) ---
    products = []
    product_id = 0
    for category, info in CATEGORIES.items():
        for _ in range(20):  # 20 products per category = 200 total
            product_id += 1
            subcat = random.choice(info["subcategories"])
            brand = random.choice(info["brands"])
            name = f"{brand} {subcat} {random.choice(['Pro', 'Plus', 'Max', 'Lite', 'Ultra', 'Classic', 'Elite', 'Eco', 'Prime', 'Basic'])} {random.choice(['X', 'V2', 'SE', '2024', 'Series', ''])}"
            name = name.strip()

            price = round(random.uniform(*info["price_range"]), 2)
            cost_ratio = random.uniform(*info["cost_ratio"])
            cost = round(price * cost_ratio, 2)
            stock = random.randint(0, 500)
            rating = round(random.uniform(2.5, 5.0), 1)
            review_count = random.randint(0, 300)

            days_ago = random.randint(1, 730)
            created_at = datetime.now() - timedelta(days=days_ago)

            products.append((
                name, category, subcat, brand, price, cost, stock,
                rating, review_count, 1, created_at.strftime("%Y-%m-%d %H:%M:%S")
            ))

    cursor.executemany(
        "INSERT INTO products (name, category, subcategory, brand, price, cost, stock_quantity, rating, review_count, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        products
    )
    logger.info(f"Inserted {len(products)} products")

    # --- Orders (2000) ---
    orders = []
    statuses = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled", "Returned"]
    status_weights = [0.05, 0.05, 0.1, 0.65, 0.1, 0.05]
    payment_methods = ["Credit Card", "Debit Card", "PayPal", "Bank Transfer", "Gift Card"]
    payment_weights = [0.4, 0.2, 0.25, 0.1, 0.05]

    for _ in range(2000):
        customer_id = random.randint(1, 500)
        days_ago = random.randint(1, 365)
        order_date = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        status = random.choices(statuses, weights=status_weights, k=1)[0]
        payment = random.choices(payment_methods, weights=payment_weights, k=1)[0]
        shipping_cost = round(random.choice([0, 4.99, 7.99, 9.99, 14.99]), 2)
        discount = round(random.choice([0, 0, 0, 5.0, 10.0, 15.0, 20.0, 25.0]), 2)

        city, state = random.choice(CITIES)
        shipping_address = f"{random.randint(1, 9999)} {random.choice(['Main', 'Oak', 'Elm'])} St, {city}, {state}"
        tracking = generate_tracking_number() if status in ["Shipped", "Delivered"] else None

        orders.append((
            customer_id, order_date.strftime("%Y-%m-%d %H:%M:%S"), status,
            0, discount, shipping_cost, payment, shipping_address, tracking
        ))

    cursor.executemany(
        "INSERT INTO orders (customer_id, order_date, status, total_amount, discount_amount, shipping_cost, payment_method, shipping_address, tracking_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        orders
    )
    logger.info(f"Inserted {len(orders)} orders")

    # --- Order Items (5000) ---
    order_items = []
    order_totals = {}

    for _ in range(5000):
        order_id = random.randint(1, 2000)
        product_id = random.randint(1, 200)

        # Get product price
        cursor.execute("SELECT price FROM products WHERE product_id = ?", (product_id,))
        row = cursor.fetchone()
        unit_price = row[0] if row else 29.99

        quantity = random.choices([1, 2, 3, 4, 5], weights=[0.5, 0.25, 0.15, 0.05, 0.05], k=1)[0]
        discount_pct = random.choice([0, 0, 0, 0, 5, 10, 15, 20])

        line_total = unit_price * quantity * (1 - discount_pct / 100)
        order_totals[order_id] = order_totals.get(order_id, 0) + line_total

        order_items.append((order_id, product_id, quantity, unit_price, discount_pct))

    cursor.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent) VALUES (?, ?, ?, ?, ?)",
        order_items
    )
    logger.info(f"Inserted {len(order_items)} order items")

    # Update order totals
    for order_id, total in order_totals.items():
        cursor.execute("UPDATE orders SET total_amount = ? WHERE order_id = ?", (round(total, 2), order_id))

    # Update customer lifetime values
    cursor.execute("""
        UPDATE customers SET lifetime_value = (
            SELECT COALESCE(SUM(o.total_amount), 0) FROM orders o
            WHERE o.customer_id = customers.customer_id AND o.status != 'Cancelled'
        )
    """)

    # --- Reviews (1500) ---
    reviews = []
    for _ in range(1500):
        product_id = random.randint(1, 200)
        customer_id = random.randint(1, 500)
        rating = random.choices([1, 2, 3, 4, 5], weights=[0.05, 0.08, 0.12, 0.35, 0.40], k=1)[0]

        if rating >= 4:
            title = random.choice(REVIEW_TITLES_POSITIVE)
            body = random.choice(REVIEW_BODIES_POSITIVE)
        else:
            title = random.choice(REVIEW_TITLES_NEGATIVE)
            body = random.choice(REVIEW_BODIES_NEGATIVE)

        helpful_votes = random.randint(0, 50)
        verified = random.choices([1, 0], weights=[0.8, 0.2], k=1)[0]
        days_ago = random.randint(1, 365)
        created_at = datetime.now() - timedelta(days=days_ago)

        reviews.append((product_id, customer_id, rating, title, body, helpful_votes, verified, created_at.strftime("%Y-%m-%d %H:%M:%S")))

    cursor.executemany(
        "INSERT INTO reviews (product_id, customer_id, rating, title, body, helpful_votes, verified_purchase, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        reviews
    )
    logger.info(f"Inserted {len(reviews)} reviews")

    # --- Inventory Log (3000) ---
    inv_logs = []
    change_types = ["Restock", "Sale", "Return", "Adjustment", "Damaged"]
    change_weights = [0.2, 0.5, 0.1, 0.15, 0.05]

    for _ in range(3000):
        product_id = random.randint(1, 200)
        change_type = random.choices(change_types, weights=change_weights, k=1)[0]

        if change_type == "Restock":
            qty_change = random.randint(10, 200)
        elif change_type == "Sale":
            qty_change = -random.randint(1, 10)
        elif change_type == "Return":
            qty_change = random.randint(1, 5)
        elif change_type == "Adjustment":
            qty_change = random.randint(-20, 20)
        else:  # Damaged
            qty_change = -random.randint(1, 5)

        prev_stock = random.randint(10, 500)
        new_stock = max(0, prev_stock + qty_change)
        notes = f"{change_type}: {'Added' if qty_change > 0 else 'Removed'} {abs(qty_change)} units"

        days_ago = random.randint(1, 365)
        created_at = datetime.now() - timedelta(days=days_ago)

        inv_logs.append((product_id, change_type, qty_change, prev_stock, new_stock, notes, created_at.strftime("%Y-%m-%d %H:%M:%S")))

    cursor.executemany(
        "INSERT INTO inventory_log (product_id, change_type, quantity_change, previous_stock, new_stock, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        inv_logs
    )
    logger.info(f"Inserted {len(inv_logs)} inventory log entries")

    conn.commit()
    conn.close()

    logger.info(f"Database seeded successfully at {db_path}")
    logger.info(f"Summary: 500 customers, 200 products, 2000 orders, 5000 order items, 1500 reviews, 3000 inventory logs")


if __name__ == "__main__":
    seed_database()
