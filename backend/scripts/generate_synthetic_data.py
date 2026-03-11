"""
Synthetic Retail Data Generator
================================
Generates 12 interrelated CSV files for the Data Scientist Agent pipeline.
Includes ~5% dirty data (nulls, mixed casing, whitespace) to keep the
cleaning agent meaningful.

Usage:
    cd backend
    python scripts/generate_synthetic_data.py
"""
from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

N_CUSTOMERS = 500
N_PRODUCTS = 200
N_SESSIONS = 8000
N_WEB_EVENTS = 10000
N_CAMPAIGNS = 100
DIRTY_RATE = 0.05  # 5% of values get dirtied

# Time range: last 12 months
END_DATE = datetime(2026, 2, 15)
START_DATE = END_DATE - timedelta(days=365)

# ---------------------------------------------------------------------------
# Authentic Reference Data
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Sarah", "James", "Emily", "Marcus", "Priya", "David", "Aisha", "Carlos",
    "Mei", "Liam", "Fatima", "Noah", "Yuki", "Oliver", "Zara", "Ethan",
    "Amara", "Lucas", "Sophia", "Raj", "Hannah", "Daniel", "Leila", "Samuel",
    "Chloe", "Ahmed", "Isabella", "Nathan", "Maya", "Ryan", "Ana", "Kevin",
    "Nadia", "Thomas", "Elena", "Brian", "Sana", "Jason", "Olivia", "Alex",
    "Grace", "Victor", "Nina", "Gabriel", "Lily", "Oscar", "Riya", "Henry",
    "Diana", "Leo", "Arjun", "Mia", "Caleb", "Rosa", "Adam", "Freya",
    "Mateo", "Clara", "Sean", "Ines", "Patrick", "Julia", "Hugo", "Vera",
    "Ian", "Amelia", "Felix", "Layla", "Erik", "Hana", "Simon", "Alina",
    "Max", "Elif", "Jack", "Luna", "Rohan", "Eva", "Derek", "Sasha",
    "Kenji", "Fiona", "Andre", "Tara", "Marco", "Iris", "Darren", "Yara",
    "Tobias", "Lucia", "Kai", "Mira", "Stefan", "Noor", "Vincent", "Jade",
    "Aiden", "Serena", "Miles", "Elsa",
]

LAST_NAMES = [
    "Johnson", "Patel", "Chen", "Williams", "Garcia", "Kim", "Brown", "Singh",
    "Martinez", "Lee", "Taylor", "Nguyen", "Anderson", "Thomas", "Muller",
    "Nakamura", "Robinson", "Ali", "Clark", "Santos", "Walker", "Hassan",
    "Young", "Wright", "Lopez", "Hill", "Scott", "Adams", "Baker", "Rivera",
    "Mitchell", "Campbell", "Torres", "Reed", "Cook", "Morgan", "Bell",
    "Murphy", "Bailey", "Cooper", "Richardson", "Cox", "Howard", "Ward",
    "Sharma", "Khan", "Ito", "Fischer", "Weber", "Becker", "Fernandez",
    "Sullivan", "Stewart", "Morris", "Rogers", "Peterson", "Cruz", "Reyes",
    "Tanaka", "Sato", "Yamamoto", "Watanabe", "Suzuki", "Cohen", "Levy",
    "Johansson", "Berg", "Larsson", "Andersen", "Jensen", "Olsen", "Meyer",
    "Hoffman", "Schulz", "Moreira", "Costa", "Pereira", "Silva", "Oliveira",
    "Rossi", "Romano", "Colombo", "Bianchi", "Dubois", "Martin", "Bernard",
    "Moreau", "Laurent", "Simon", "Lemoine", "Petit", "Durand", "Leroy",
    "Roux", "David", "Bertrand", "Girard", "Fontaine", "Chevalier", "Blanc",
]

EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "protonmail.com"]

PRODUCT_CATALOG = {
    "Electronics": [
        ("Sony WH-1000XM5 Headphones", "Sony"), ("Samsung Galaxy S24 Case", "Samsung"),
        ("Anker USB-C Hub 7-in-1", "Anker"), ("Apple AirPods Pro 2nd Gen", "Apple"),
        ("Bose QuietComfort Earbuds", "Bose"), ("Logitech MX Master 3S Mouse", "Logitech"),
        ("JBL Flip 6 Bluetooth Speaker", "JBL"), ("Belkin Wireless Charging Pad", "Belkin"),
        ("SanDisk 256GB Flash Drive", "SanDisk"), ("Kindle Paperwhite 11th Gen", "Amazon"),
        ("Razer DeathAdder V3 Mouse", "Razer"), ("Corsair K70 RGB Keyboard", "Corsair"),
        ("TP-Link Deco Mesh WiFi 6", "TP-Link"), ("GoPro Hero 12 Black", "GoPro"),
        ("Roku Streaming Stick 4K+", "Roku"), ("Samsung T7 Portable SSD 1TB", "Samsung"),
        ("Apple Watch SE Band", "Apple"), ("Anker PowerCore 10000mAh", "Anker"),
        ("Ring Video Doorbell 4", "Ring"), ("Fitbit Charge 6 Tracker", "Fitbit"),
        ("Lenovo Tab M10 Plus", "Lenovo"), ("Google Chromecast HD", "Google"),
        ("HyperX Cloud II Headset", "HyperX"), ("Dell USB-C Monitor Cable", "Dell"),
        ("Philips Hue Smart Bulb A19", "Philips"),
    ],
    "Clothing": [
        ("Levi's 501 Original Jeans", "Levi's"), ("Nike Dri-FIT Running Tee", "Nike"),
        ("Patagonia Down Jacket", "Patagonia"), ("Adidas Ultraboost 22 Shoes", "Adidas"),
        ("H&M Slim Fit Chinos", "H&M"), ("The North Face Puffer Vest", "The North Face"),
        ("Uniqlo Heattech Long Sleeve", "Uniqlo"), ("Calvin Klein Boxer Briefs 3-Pack", "Calvin Klein"),
        ("Zara Oversized Blazer", "Zara"), ("Gap Classic Logo Hoodie", "Gap"),
        ("Hanes Comfort Crew Socks 6pk", "Hanes"), ("Columbia Fleece Quarter-Zip", "Columbia"),
        ("Tommy Hilfiger Polo Shirt", "Tommy Hilfiger"), ("Under Armour Tech 2.0 Tee", "Under Armour"),
        ("Brooks Ghost 15 Running Shoe", "Brooks"), ("Carhartt Beanie Watch Cap", "Carhartt"),
        ("Wrangler Straight Fit Jeans", "Wrangler"), ("Puma Essential Track Pants", "Puma"),
        ("New Balance 574 Sneakers", "New Balance"), ("Ralph Lauren Oxford Shirt", "Ralph Lauren"),
        ("Champion Reverse Weave Crew", "Champion"), ("Vans Old Skool Classic", "Vans"),
        ("Converse Chuck Taylor All Star", "Converse"), ("Timberland 6-Inch Boot", "Timberland"),
        ("Reebok Classic Leather", "Reebok"),
    ],
    "Beauty": [
        ("CeraVe Moisturizing Cream 16oz", "CeraVe"), ("Maybelline Fit Me Foundation", "Maybelline"),
        ("The Ordinary Niacinamide 10%", "The Ordinary"), ("Neutrogena Hydro Boost Gel", "Neutrogena"),
        ("L'Oreal Revitalift Eye Cream", "L'Oreal"), ("NYX Soft Matte Lip Cream", "NYX"),
        ("Dove Body Wash Deep Moisture", "Dove"), ("Olay Regenerist Micro-Sculpting", "Olay"),
        ("Clinique Moisture Surge 72hr", "Clinique"), ("MAC Ruby Woo Lipstick", "MAC"),
        ("Garnier Micellar Cleansing Water", "Garnier"), ("Cetaphil Gentle Skin Cleanser", "Cetaphil"),
        ("Aveeno Daily Moisturizing Lotion", "Aveeno"), ("Urban Decay All Nighter Spray", "Urban Decay"),
        ("La Roche-Posay Toleriane Cleanser", "La Roche-Posay"), ("Revlon ColorStay Eyeliner", "Revlon"),
        ("Bioderma Sensibio H2O Micellar", "Bioderma"), ("ELF Poreless Putty Primer", "ELF"),
        ("Eucerin Advanced Repair Cream", "Eucerin"), ("Aquaphor Healing Ointment", "Aquaphor"),
        ("Vaseline Intensive Care Lotion", "Vaseline"), ("Burt's Bees Lip Balm Original", "Burt's Bees"),
        ("St. Ives Apricot Scrub", "St. Ives"), ("Nivea Soft Moisturizing Cream", "Nivea"),
        ("Pantene Pro-V Daily Shampoo", "Pantene"),
    ],
    "Sports": [
        ("Yoga Mat Pro 6mm Non-Slip", "Gaiam"), ("Wilson NCAA Official Basketball", "Wilson"),
        ("Hydro Flask 32oz Wide Mouth", "Hydro Flask"), ("Fitbit Inspire 3 Band", "Fitbit"),
        ("TRX Suspension Trainer Kit", "TRX"), ("Speedo Vanquisher 2.0 Goggles", "Speedo"),
        ("CAP Barbell Dumbbell Set 20lb", "CAP"), ("Manduka PRO Yoga Mat 71in", "Manduka"),
        ("Nike Training Gloves Unisex", "Nike"), ("Theraband Resistance Loop Set", "Theraband"),
        ("SKLZ Speed Agility Ladder", "SKLZ"), ("Trigger Point GRID Foam Roller", "Trigger Point"),
        ("Coleman Portable Camp Chair", "Coleman"), ("Garmin Forerunner 55 Watch", "Garmin"),
        ("Osprey Daylite Plus Backpack", "Osprey"), ("Yeti Rambler 26oz Bottle", "Yeti"),
        ("Bowflex SelectTech 552 Dumbbell", "Bowflex"), ("Callaway Supersoft Golf Balls", "Callaway"),
        ("HEAD Penn Championship Tennis Balls", "HEAD"), ("Mueller Sports Ankle Brace", "Mueller"),
        ("Perfect Fitness Ab Roller", "Perfect Fitness"), ("Everlast Pro Boxing Gloves", "Everlast"),
        ("Schwinn Bike Pump Floor Model", "Schwinn"), ("Camelbak Podium Water Bottle", "Camelbak"),
        ("Spalding NBA Replica Basketball", "Spalding"),
    ],
    "Books": [
        ("Atomic Habits by James Clear", "Penguin"), ("The Midnight Library by Matt Haig", "Viking"),
        ("Project Hail Mary by Andy Weir", "Ballantine"), ("Educated by Tara Westover", "Random House"),
        ("Dune by Frank Herbert", "Ace"), ("The Alchemist by Paulo Coelho", "HarperOne"),
        ("Sapiens by Yuval Noah Harari", "Harper"), ("Thinking Fast and Slow by Kahneman", "FSG"),
        ("The Great Gatsby by Fitzgerald", "Scribner"), ("1984 by George Orwell", "Signet"),
        ("To Kill a Mockingbird by Harper Lee", "Grand Central"), ("The Power of Now by Eckhart Tolle", "New World"),
        ("Becoming by Michelle Obama", "Crown"), ("The Body Keeps the Score", "Penguin"),
        ("Where the Crawdads Sing", "Putnam"), ("Rich Dad Poor Dad by Kiyosaki", "Plata"),
        ("The Subtle Art of Not Giving", "Harper"), ("Deep Work by Cal Newport", "Grand Central"),
        ("Think and Grow Rich by Hill", "TarcherPerigee"), ("The 48 Laws of Power by Greene", "Penguin"),
        ("Man's Search for Meaning", "Beacon"), ("The Four Agreements by Ruiz", "Amber-Allen"),
        ("Outliers by Malcolm Gladwell", "Back Bay"), ("The Lean Startup by Eric Ries", "Currency"),
        ("Good to Great by Jim Collins", "HarperBusiness"),
    ],
    "Home": [
        ("Instant Pot Duo 7-in-1 6Qt", "Instant Pot"), ("Philips Hue Starter Kit 4-Pack", "Philips"),
        ("Dyson V15 Detect Vacuum", "Dyson"), ("KitchenAid Stand Mixer 5Qt", "KitchenAid"),
        ("Nest Learning Thermostat 3rd", "Google Nest"), ("Casper Original Pillow", "Casper"),
        ("iRobot Roomba i3+ Robot Vacuum", "iRobot"), ("Calphalon Classic 10pc Cookware", "Calphalon"),
        ("Yankee Candle Large Jar Vanilla", "Yankee"), ("Brita Standard Water Filter", "Brita"),
        ("AmazonBasics Microfiber Sheets", "AmazonBasics"), ("Lodge Cast Iron Skillet 12in", "Lodge"),
        ("Keurig K-Mini Coffee Maker", "Keurig"), ("Rubbermaid Food Storage 42pc", "Rubbermaid"),
        ("OXO Good Grips Cutting Board", "OXO"), ("Cuisinart 14-Cup Food Processor", "Cuisinart"),
        ("Weber Spirit E-310 Gas Grill", "Weber"), ("Ninja Professional Blender 72oz", "Ninja"),
        ("SimpliSafe Home Security Kit", "SimpliSafe"), ("Shark Steam Mop S1000", "Shark"),
        ("Pyrex Glass Measuring Cup Set", "Pyrex"), ("Mr Coffee 12-Cup Programmable", "Mr Coffee"),
        ("BLACK+DECKER Toaster Oven", "BLACK+DECKER"), ("Hamilton Beach Slow Cooker 6Qt", "Hamilton Beach"),
        ("Swiffer WetJet Starter Kit", "Swiffer"),
    ],
    "Toys": [
        ("LEGO Creator 3-in-1 Treehouse", "LEGO"), ("Monopoly Classic Board Game", "Hasbro"),
        ("Barbie Dreamhouse 2024 Edition", "Mattel"), ("Hot Wheels 20-Car Gift Pack", "Hot Wheels"),
        ("Catan Board Game 5th Edition", "Catan Studio"), ("Play-Doh 10-Pack Bundle", "Play-Doh"),
        ("Nerf Elite 2.0 Eaglepoint", "Nerf"), ("UNO Card Game Classic", "Mattel"),
        ("Fisher-Price Laugh & Learn", "Fisher-Price"), ("Melissa & Doug Wooden Puzzle", "Melissa & Doug"),
        ("Risk Strategy Board Game", "Hasbro"), ("Pokemon Trading Card Elite Box", "Pokemon"),
        ("Magna-Tiles Clear Colors 32pc", "Magna-Tiles"), ("Jenga Classic Block Game", "Hasbro"),
        ("Nintendo Switch Joy-Con Set", "Nintendo"), ("Rubik's Cube 3x3 Original", "Rubik's"),
        ("Crayola 120ct Crayon Box", "Crayola"), ("Transformers Action Figure", "Hasbro"),
        ("Baby Einstein Discovery Blocks", "Baby Einstein"), ("VTech KidiZoom Camera Pix", "VTech"),
        ("Razor A Kick Scooter", "Razor"), ("Hatchimals Mystery Egg", "Spin Master"),
        ("K'NEX Building Set 705pc", "K'NEX"), ("Disney Princess Dress-Up Set", "Disney"),
        ("Ticket to Ride Board Game", "Days of Wonder"),
    ],
    "Food": [
        ("Organic Green Tea Matcha 4oz", "Jade Leaf"), ("KIND Protein Bars Variety 12pk", "KIND"),
        ("Blue Diamond Almonds 16oz", "Blue Diamond"), ("Quaker Oats Old Fashioned 42oz", "Quaker"),
        ("Clif Bar Energy Variety 12pk", "Clif"), ("Annie's Organic Mac & Cheese 6pk", "Annie's"),
        ("Starbucks Pike Place K-Cups 72", "Starbucks"), ("RXBar Protein Bar Variety 12pk", "RXBar"),
        ("Kirkland Mixed Nuts 2.5lb", "Kirkland"), ("Nespresso Original Capsules 50pk", "Nespresso"),
        ("Nature Valley Granola Bars 48ct", "Nature Valley"), ("Ghirardelli Dark Chocolate Squares", "Ghirardelli"),
        ("Wonderful Pistachios 16oz", "Wonderful"), ("Lavazza Super Crema Espresso", "Lavazza"),
        ("Justin's Classic Almond Butter", "Justin's"), ("Tillamook Sharp Cheddar 2lb", "Tillamook"),
        ("Celsius Energy Drink Variety 12", "Celsius"), ("Liquid Death Mountain Water 12", "Liquid Death"),
        ("Skinny Pop Popcorn 12pk", "Skinny Pop"), ("Belvita Breakfast Biscuits 30ct", "Belvita"),
        ("Trader Joe's Everything Seasoning", "Trader Joe's"), ("Kodiak Cakes Pancake Mix 24oz", "Kodiak"),
        ("Chobani Greek Yogurt Variety 12", "Chobani"), ("Bob's Red Mill Oat Flour 20oz", "Bob's Red Mill"),
        ("Lara Bar Variety Pack 18ct", "Lara Bar"),
    ],
}

LOCATIONS = [
    "New York, USA", "Los Angeles, USA", "Chicago, USA", "Houston, USA",
    "Mumbai, India", "Delhi, India", "Bangalore, India",
    "London, UK", "Berlin, Germany", "Paris, France",
    "Tokyo, Japan", "Sydney, Australia", "Toronto, Canada",
    "São Paulo, Brazil", "Dubai, UAE",
]
DEVICES = ["mobile", "desktop", "tablet"]
CATEGORIES = list(PRODUCT_CATALOG.keys())
GENDERS = ["Male", "Female", "Non-binary", "Prefer not to say"]
LOYALTY_STATUSES = ["bronze", "silver", "gold", "platinum"]
PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "wallet", "bank_transfer"]
PAYMENT_STATUSES = ["completed", "pending", "failed", "refunded"]
ORDER_STATUSES = ["delivered", "shipped", "processing", "cancelled", "returned"]
CURRENCIES = ["USD", "EUR", "GBP", "CAD", "INR", "AUD", "BRL", "JPY"]
SUPPLIERS = ["GlobalSupplyCo", "PrimeWholesale", "UrbanTraders", "MegaDistro", "FastShip",
             "NexGen Logistics", "Pacific Trading", "Atlas Distribution", "Pinnacle Supply", "CoreFreight"]
WAREHOUSES = ["WH-NY", "WH-LA", "WH-LON", "WH-TOR", "WH-MUM", "WH-SYD"]
CHANNELS = ["email", "google_ads", "facebook", "instagram", "in_app", "social"]
CAMPAIGN_TYPES = ["seasonal_sale", "new_arrival", "clearance", "loyalty", "flash_sale"]
TRAFFIC_SOURCES = ["organic_search", "paid_search", "email", "social", "direct", "referral"]
PAGE_TYPES = ["home", "product", "category", "cart", "checkout", "search_results"]
ACTIONS = ["view_page", "add_to_cart", "remove_from_cart", "purchase", "search"]
REFERRAL_SOURCES = ["direct", "organic_search", "email", "social", "paid_ads"]
EVENT_TYPES = ["page_view", "product_view", "add_to_cart", "begin_checkout", "purchase"]
LANDING_PAGES = ["home", "product", "category", "deals", "new_arrivals", "search"]

CAMPAIGN_NAME_TEMPLATES = [
    "Summer Blowout {year}", "Back to School Sale", "Black Friday Electronics",
    "Holiday Gift Guide {year}", "Spring Clearance", "Winter Warmup Deals",
    "New Year New You {year}", "Valentine's Day Specials", "Flash Sale Weekend",
    "Cyber Monday Deals", "End of Season Clearance", "Loyalty Rewards Week",
    "Easter Weekend Sale", "Labor Day Savings", "Fall Fashion Preview",
    "Prime Day Rivals", "Diwali Festive Sale", "Christmas Countdown",
    "Mid-Year Mega Sale", "Anniversary Special",
]


# ---------------------------------------------------------------------------
# Dirty-data injection helpers
# ---------------------------------------------------------------------------

def dirty_string(val: str) -> str:
    """Randomly mess up a string value."""
    r = random.random()
    if r < 0.25:
        return f" {val.lower()} "
    elif r < 0.5:
        return val.upper()
    elif r < 0.75:
        return f" {val} "
    else:
        return val.lower()


def maybe_null(val, rate: float = DIRTY_RATE):
    """Replace a value with NaN at the given rate."""
    if random.random() < rate:
        return np.nan
    return val


def maybe_dirty_str(val: str, rate: float = DIRTY_RATE):
    """Possibly dirty a string value."""
    if val is None:
        return val
    if random.random() < rate:
        return dirty_string(val)
    return val


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


# ---------------------------------------------------------------------------
# Pre-build product list (flattened with category + brand)
# ---------------------------------------------------------------------------

def _build_product_pool():
    """Build a flat list of (product_name, category, brand) tuples."""
    pool = []
    for category, items in PRODUCT_CATALOG.items():
        for product_name, brand in items:
            pool.append((product_name, category, brand))
    return pool


PRODUCT_POOL = _build_product_pool()  # 200 products total


def _build_name_pool(n: int):
    """Generate n unique full names."""
    names = set()
    while len(names) < n:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        names.add(f"{first} {last}")
    return list(names)


def _make_email(name: str) -> str:
    """Derive an email from a full name."""
    parts = name.lower().replace("'", "").replace(".", "").split()
    base = ".".join(parts)
    num = random.randint(1, 99)
    domain = random.choice(EMAIL_DOMAINS)
    return f"{base}{num}@{domain}"


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_customers() -> pd.DataFrame:
    names = _build_name_pool(N_CUSTOMERS)
    rows = []
    for i in range(N_CUSTOMERS):
        cid = f"CUST{1000 + i}"
        name = names[i]
        rows.append({
            "customer_id": maybe_null(maybe_dirty_str(cid, 0.02)),
            "name": maybe_null(maybe_dirty_str(name, 0.03)),
            "email": maybe_null(_make_email(name)),
            "age": maybe_null(random.randint(18, 70)),
            "gender": maybe_null(maybe_dirty_str(
                random.choices(GENDERS, weights=[40, 40, 10, 10])[0]
            )),
            "location": maybe_null(maybe_dirty_str(random.choice(LOCATIONS))),
            "device_type": maybe_null(maybe_dirty_str(random.choice(DEVICES))),
            "loyalty_status": maybe_null(maybe_dirty_str(
                random.choices(LOYALTY_STATUSES, weights=[40, 30, 20, 10])[0]
            )),
            "total_spend": 0.0,  # will be backfilled after transactions
            "acquisition_date": maybe_null(
                random_date(START_DATE - timedelta(days=365), END_DATE).strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )
            ),
        })
    return pd.DataFrame(rows)


def generate_products() -> pd.DataFrame:
    pool = PRODUCT_POOL.copy()
    random.shuffle(pool)
    rows = []
    for i in range(N_PRODUCTS):
        sku = f"SKU{10000 + i}"
        product_name, category, brand = pool[i % len(pool)]
        cost = round(random.uniform(5, 200), 2)
        retail = round(cost * random.uniform(1.3, 3.0), 2)
        margin = round((retail - cost) / retail, 4) if retail > 0 else 0.0
        discount = random.choice([0, 0, 0, 5, 10, 15, 20, 25, 30])
        rating = round(random.uniform(1.0, 5.0), 2)

        rows.append({
            "sku": maybe_null(maybe_dirty_str(sku, 0.02)),
            "product_name": maybe_null(maybe_dirty_str(product_name, 0.03)),
            "category": maybe_null(maybe_dirty_str(category)),
            "brand": maybe_null(maybe_dirty_str(brand)),
            "cost_price": maybe_null(cost),
            "retail_price": maybe_null(retail),
            "profit_margin": maybe_null(margin),
            "discount_percent": maybe_null(float(discount)),
            "average_rating": maybe_null(rating),
        })
    return pd.DataFrame(rows)


def generate_marketing() -> pd.DataFrame:
    rows = []
    year = END_DATE.year
    campaign_names = [t.format(year=year) for t in CAMPAIGN_NAME_TEMPLATES]

    for i in range(N_CAMPAIGNS):
        cid = f"CAMP{3000 + i}"
        start = random_date(START_DATE, END_DATE - timedelta(days=30))
        end = start + timedelta(days=random.randint(14, 90))
        impressions = random.randint(5000, 100000)
        clicks = int(impressions * random.uniform(0.01, 0.06))
        conversions = int(clicks * random.uniform(0.02, 0.15))
        spend = round(random.uniform(50, 5000), 2)
        c_name = random.choice(campaign_names)

        rows.append({
            "campaign_id": maybe_null(maybe_dirty_str(cid, 0.02)),
            "channel": maybe_null(maybe_dirty_str(random.choice(CHANNELS))),
            "campaign_type": maybe_null(maybe_dirty_str(random.choice(CAMPAIGN_TYPES))),
            "campaign_name": maybe_null(maybe_dirty_str(c_name, 0.03)),
            "start_date": maybe_null(start.strftime("%Y-%m-%d")),
            "end_date": maybe_null(end.strftime("%Y-%m-%d")),
            "ad_spend": maybe_null(spend),
            "impressions": maybe_null(float(impressions)),
            "clicks": maybe_null(float(clicks)),
            "conversions": maybe_null(float(conversions)),
        })
    return pd.DataFrame(rows)


def generate_inventory(products: pd.DataFrame) -> pd.DataFrame:
    valid_skus = products["sku"].dropna().tolist()
    rows = []
    for sku in valid_skus:
        rows.append({
            "sku": maybe_dirty_str(str(sku), 0.02),
            "stock_quantity": maybe_null(float(random.randint(10, 500))),
            "reorder_level": maybe_null(float(random.randint(20, 80))),
            "warehouse_location": maybe_null(maybe_dirty_str(random.choice(WAREHOUSES))),
            "supplier": maybe_null(maybe_dirty_str(random.choice(SUPPLIERS))),
        })
    return pd.DataFrame(rows)


def generate_sessions(customers: pd.DataFrame, marketing: pd.DataFrame) -> pd.DataFrame:
    valid_cids = customers["customer_id"].dropna().tolist()

    # Build active campaign lookup: list of (channel, campaign_name, start, end)
    active_campaigns = []
    for _, row in marketing.iterrows():
        try:
            c_name = row.get("campaign_name")
            channel = row.get("channel")
            sd = row.get("start_date")
            ed = row.get("end_date")
            if pd.notna(c_name) and pd.notna(sd) and pd.notna(ed):
                active_campaigns.append((
                    str(channel), str(c_name),
                    datetime.strptime(str(sd), "%Y-%m-%d"),
                    datetime.strptime(str(ed), "%Y-%m-%d"),
                ))
        except (ValueError, TypeError):
            continue

    rows = []
    session_ids = []
    for i in range(N_SESSIONS):
        sid = f"SESS{100000 + i}"
        cid = random.choice(valid_cids)
        sess_start = random_date(START_DATE, END_DATE)
        duration_sec = random.randint(30, 1800)
        sess_end = sess_start + timedelta(seconds=duration_sec)
        pages = random.randint(1, 20)
        device = random.choice(DEVICES)
        landing = random.choice(LANDING_PAGES)
        source = random.choice(TRAFFIC_SOURCES)

        # Campaign attribution: link session to an active campaign if source matches
        camp_name = None
        if source in ("paid_search", "email", "social"):
            matching = [
                c for c in active_campaigns
                if c[2] <= sess_start <= c[3]
            ]
            if matching:
                chosen = random.choice(matching)
                camp_name = chosen[1]

        converted = random.random() < 0.20  # 20% conversion rate
        revenue = round(random.uniform(15, 500), 2) if converted else 0.0

        session_ids.append(sid)
        rows.append({
            "session_id": maybe_null(maybe_dirty_str(sid, 0.02)),
            "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)),
            "session_start": maybe_null(sess_start.strftime("%Y-%m-%d %H:%M:%S.%f")),
            "session_end": maybe_null(sess_end.strftime("%Y-%m-%d %H:%M:%S.%f")),
            "session_duration_sec": maybe_null(float(duration_sec)),
            "pages_viewed": maybe_null(float(pages)),
            "device_type": maybe_null(maybe_dirty_str(device)),
            "landing_page": maybe_null(maybe_dirty_str(landing)),
            "traffic_source": maybe_null(maybe_dirty_str(source)),
            "campaign_name": maybe_null(maybe_dirty_str(camp_name, 0.03)) if camp_name else np.nan,
            "converted_flag": maybe_null(converted),
            "revenue": maybe_null(revenue),
        })
    return pd.DataFrame(rows)


def generate_events(sessions: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    valid_skus = products["sku"].dropna().tolist()
    sku_prices = dict(zip(products["sku"].dropna(), products["retail_price"].dropna()))

    rows = []
    event_counter = 200000

    for _, sess in sessions.iterrows():
        sid = sess.get("session_id")
        cid = sess.get("customer_id")
        converted = sess.get("converted_flag")
        sess_start_str = sess.get("session_start")

        if pd.isna(sid) or pd.isna(sess_start_str):
            continue

        try:
            sess_start = datetime.strptime(str(sess_start_str).strip(), "%Y-%m-%d %H:%M:%S.%f")
        except (ValueError, TypeError):
            continue

        duration = sess.get("session_duration_sec")
        if pd.isna(duration):
            duration = 300
        duration = int(float(duration))

        def _evt_offset(lo, hi):
            """Safe random offset clamped to session duration."""
            lo = min(lo, duration)
            hi = min(hi, duration)
            if lo >= hi:
                return lo
            return random.randint(lo, hi)

        # Every session: page_view
        eid = f"EVT{event_counter}"
        event_counter += 1
        evt_time = sess_start + timedelta(seconds=_evt_offset(0, 10))
        rows.append({
            "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
            "session_id": maybe_null(maybe_dirty_str(str(sid), 0.03)),
            "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)) if pd.notna(cid) else np.nan,
            "event_type": maybe_null(maybe_dirty_str("page_view")),
            "event_datetime": maybe_null(evt_time.strftime("%Y-%m-%d %H:%M:%S.%f")),
            "sku": np.nan,
            "quantity": np.nan,
            "unit_price": np.nan,
        })

        # ~70% get product_view
        if random.random() < 0.70:
            eid = f"EVT{event_counter}"
            event_counter += 1
            sku = random.choice(valid_skus)
            price = sku_prices.get(sku, round(random.uniform(10, 300), 2))
            if isinstance(price, float) and np.isnan(price):
                price = round(random.uniform(10, 300), 2)
            evt_time = sess_start + timedelta(seconds=_evt_offset(10, 60))
            rows.append({
                "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
                "session_id": maybe_null(maybe_dirty_str(str(sid), 0.03)),
                "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)) if pd.notna(cid) else np.nan,
                "event_type": maybe_null(maybe_dirty_str("product_view")),
                "event_datetime": maybe_null(evt_time.strftime("%Y-%m-%d %H:%M:%S.%f")),
                "sku": maybe_null(maybe_dirty_str(str(sku), 0.03)),
                "quantity": np.nan,
                "unit_price": maybe_null(price),
            })

            # ~30% (of all sessions) get add_to_cart
            if random.random() < 0.43:  # 0.43 * 0.70 ≈ 0.30
                eid = f"EVT{event_counter}"
                event_counter += 1
                qty = random.randint(1, 4)
                evt_time = sess_start + timedelta(seconds=_evt_offset(60, 180))
                rows.append({
                    "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
                    "session_id": maybe_null(maybe_dirty_str(str(sid), 0.03)),
                    "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)) if pd.notna(cid) else np.nan,
                    "event_type": maybe_null(maybe_dirty_str("add_to_cart")),
                    "event_datetime": maybe_null(evt_time.strftime("%Y-%m-%d %H:%M:%S.%f")),
                    "sku": maybe_null(maybe_dirty_str(str(sku), 0.03)),
                    "quantity": maybe_null(float(qty)),
                    "unit_price": maybe_null(price),
                })

                # ~15% (of all sessions) get begin_checkout
                if random.random() < 0.50:  # 0.50 * 0.43 * 0.70 ≈ 0.15
                    eid = f"EVT{event_counter}"
                    event_counter += 1
                    evt_time = sess_start + timedelta(seconds=_evt_offset(180, 300))
                    rows.append({
                        "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
                        "session_id": maybe_null(maybe_dirty_str(str(sid), 0.03)),
                        "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)) if pd.notna(cid) else np.nan,
                        "event_type": maybe_null(maybe_dirty_str("begin_checkout")),
                        "event_datetime": maybe_null(evt_time.strftime("%Y-%m-%d %H:%M:%S.%f")),
                        "sku": maybe_null(maybe_dirty_str(str(sku), 0.03)),
                        "quantity": maybe_null(float(qty)),
                        "unit_price": maybe_null(price),
                    })

                    # Only converted sessions get purchase
                    if converted is True or (isinstance(converted, (bool, np.bool_)) and converted):
                        eid = f"EVT{event_counter}"
                        event_counter += 1
                        evt_time = sess_start + timedelta(seconds=_evt_offset(300, 600))
                        rows.append({
                            "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
                            "session_id": maybe_null(maybe_dirty_str(str(sid), 0.03)),
                            "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)) if pd.notna(cid) else np.nan,
                            "event_type": maybe_null(maybe_dirty_str("purchase")),
                            "event_datetime": maybe_null(evt_time.strftime("%Y-%m-%d %H:%M:%S.%f")),
                            "sku": maybe_null(maybe_dirty_str(str(sku), 0.03)),
                            "quantity": maybe_null(float(qty)),
                            "unit_price": maybe_null(price),
                        })

    return pd.DataFrame(rows)


def generate_web_analytics(sessions: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    valid_sids = sessions["session_id"].dropna().tolist()
    valid_cids = customers["customer_id"].dropna().tolist()
    rows = []

    for i in range(N_WEB_EVENTS):
        eid = f"WEB{300000 + i}"
        sid = random.choice(valid_sids)
        cid = random.choice(valid_cids)
        action = random.choice(ACTIONS)
        add_to_cart = action == "add_to_cart"

        rows.append({
            "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
            "session_id": maybe_null(maybe_dirty_str(str(sid), 0.03)),
            "customer_id": maybe_dirty_str(str(cid), 0.03),
            "event_datetime": maybe_null(
                random_date(START_DATE, END_DATE).strftime("%Y-%m-%d %H:%M:%S.%f")
            ),
            "page_type": maybe_null(maybe_dirty_str(random.choice(PAGE_TYPES))),
            "action": maybe_null(maybe_dirty_str(action)),
            "add_to_cart": maybe_null(add_to_cart),
            "referral_source": maybe_null(maybe_dirty_str(random.choice(REFERRAL_SOURCES))),
        })
    return pd.DataFrame(rows)


def generate_transactions(sessions: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Generate transactions from converted sessions."""
    valid_skus = products["sku"].dropna().tolist()
    sku_prices = dict(zip(products["sku"].dropna(), products["retail_price"].dropna()))

    rows = []
    order_counter = 5000
    txn_session_map = []  # track (order_id, session_id) for transactions_with_session

    converted_sessions = sessions[sessions["converted_flag"] == True]  # noqa: E712

    for _, sess in converted_sessions.iterrows():
        sid = sess.get("session_id")
        cid = sess.get("customer_id")
        sess_start_str = sess.get("session_start")
        revenue = sess.get("revenue", 0)

        if pd.isna(sid) or pd.isna(cid):
            continue

        try:
            if pd.notna(sess_start_str):
                order_dt = datetime.strptime(str(sess_start_str).strip(), "%Y-%m-%d %H:%M:%S.%f")
            else:
                order_dt = random_date(START_DATE, END_DATE)
        except (ValueError, TypeError):
            order_dt = random_date(START_DATE, END_DATE)

        # Each converted session generates 1-5 order lines
        n_items = random.randint(1, 5)
        for _ in range(n_items):
            oid = f"ORD{order_counter}"
            order_counter += 1
            sku = random.choice(valid_skus)
            qty = random.randint(1, 5)
            price = sku_prices.get(sku, round(random.uniform(10, 500), 2))
            if isinstance(price, float) and np.isnan(price):
                price = round(random.uniform(10, 500), 2)
            total = round(qty * price, 2)
            discount_amt = round(total * random.choice([0, 0, 0, 0.05, 0.10, 0.15, 0.20]), 2)

            status = random.choices(ORDER_STATUSES, weights=[60, 15, 10, 10, 5])[0]

            rows.append({
                "order_id": maybe_null(maybe_dirty_str(oid, 0.02)),
                "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)),
                "sku": maybe_null(maybe_dirty_str(str(sku), 0.03)),
                "quantity": maybe_null(float(qty)),
                "unit_price": maybe_null(price),
                "total_amount": maybe_null(total),
                "discount_amount": maybe_null(discount_amt),
                "order_status": maybe_null(maybe_dirty_str(status)),
                "order_datetime": maybe_null(
                    order_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                ),
            })
            txn_session_map.append({"order_id": oid, "session_id": str(sid)})

    df = pd.DataFrame(rows)
    return df, txn_session_map


def generate_payments(transactions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, txn in transactions.iterrows():
        oid = txn.get("order_id", "")
        rows.append({
            "order_id": maybe_null(maybe_dirty_str(str(oid), 0.03)) if pd.notna(oid) else np.nan,
            "payment_method": maybe_null(maybe_dirty_str(random.choice(PAYMENT_METHODS))),
            "payment_status": maybe_null(maybe_dirty_str(
                random.choices(PAYMENT_STATUSES, weights=[75, 10, 5, 10])[0]
            )),
            "transaction_fee": maybe_null(round(random.uniform(0.5, 25), 2)),
            "currency": maybe_null(maybe_dirty_str(random.choice(CURRENCIES))),
        })
    return pd.DataFrame(rows)


def generate_campaign_performance(
    marketing: pd.DataFrame, sessions: pd.DataFrame, transactions_with_session: pd.DataFrame
) -> pd.DataFrame:
    """Aggregate daily campaign performance from marketing, sessions, and transactions."""
    rows = []

    for _, camp in marketing.iterrows():
        camp_id = camp.get("campaign_id")
        channel = camp.get("channel")
        c_name = camp.get("campaign_name")
        sd_str = camp.get("start_date")
        ed_str = camp.get("end_date")
        total_impressions = camp.get("impressions", 0)
        total_clicks = camp.get("clicks", 0)
        total_spend = camp.get("ad_spend", 0)

        if pd.isna(sd_str) or pd.isna(ed_str) or pd.isna(camp_id):
            continue

        try:
            sd = datetime.strptime(str(sd_str), "%Y-%m-%d")
            ed = datetime.strptime(str(ed_str), "%Y-%m-%d")
        except (ValueError, TypeError):
            continue

        n_days = max((ed - sd).days, 1)

        # Distribute totals across days with some noise
        for day_offset in range(n_days):
            date = sd + timedelta(days=day_offset)
            if date > END_DATE:
                break

            # Daily share with noise
            noise = random.uniform(0.5, 1.5)
            daily_imp = int((float(total_impressions) / n_days) * noise) if pd.notna(total_impressions) else 0
            daily_clicks = int((float(total_clicks) / n_days) * noise) if pd.notna(total_clicks) else 0
            daily_spend = round((float(total_spend) / n_days) * noise, 2) if pd.notna(total_spend) else 0

            # Simulated sessions/orders for this campaign-day
            daily_sessions = random.randint(0, 15)
            daily_orders = random.randint(0, max(1, daily_sessions // 5))
            daily_revenue = round(daily_orders * random.uniform(20, 200), 2)

            rows.append({
                "date": maybe_null(date.strftime("%Y-%m-%d")),
                "campaign_id": maybe_null(maybe_dirty_str(str(camp_id), 0.02)),
                "channel": maybe_null(maybe_dirty_str(str(channel))) if pd.notna(channel) else np.nan,
                "campaign_name": maybe_null(maybe_dirty_str(str(c_name), 0.03)) if pd.notna(c_name) else np.nan,
                "impressions": maybe_null(float(daily_imp)),
                "clicks": maybe_null(float(daily_clicks)),
                "spend": maybe_null(daily_spend),
                "sessions": maybe_null(float(daily_sessions)),
                "orders": maybe_null(float(daily_orders)),
                "attributed_revenue": maybe_null(daily_revenue),
            })

    return pd.DataFrame(rows)


def generate_funnel_summary(events: pd.DataFrame, sessions: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily funnel metrics from events and sessions."""
    # Build daily counts from events
    rows = []
    n_days = (END_DATE - START_DATE).days

    # Pre-compute event type counts by date (using clean dates from the range)
    for day_offset in range(n_days):
        date = START_DATE + timedelta(days=day_offset)
        date_str = date.strftime("%Y-%m-%d")

        # Simulated realistic daily funnel numbers
        daily_sessions = random.randint(20, 80)
        product_views = int(daily_sessions * random.uniform(0.5, 0.8))
        add_to_cart = int(product_views * random.uniform(0.2, 0.4))
        checkout_started = int(add_to_cart * random.uniform(0.3, 0.6))
        purchases = int(checkout_started * random.uniform(0.4, 0.7))

        conv_rate = round(purchases / daily_sessions, 4) if daily_sessions > 0 else 0
        cart_abandon = round(1 - (purchases / add_to_cart), 4) if add_to_cart > 0 else 0

        rows.append({
            "date": maybe_null(date_str),
            "sessions": maybe_null(float(daily_sessions)),
            "product_views": maybe_null(float(product_views)),
            "add_to_cart": maybe_null(float(add_to_cart)),
            "checkout_started": maybe_null(float(checkout_started)),
            "purchases": maybe_null(float(purchases)),
            "conversion_rate": maybe_null(conv_rate),
            "cart_abandonment_rate": maybe_null(cart_abandon),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_all_data(local: bool = False) -> dict:
    """Generate all 12 synthetic datasets and save to Supabase (or local CSV).

    Args:
        local: If True, write CSVs to data/raw/ instead of Supabase.

    Returns:
        Dict with dataset name -> row count.
    """
    if local:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        for f in RAW_DIR.glob("*.csv"):
            f.unlink()
            print(f"  Removed old file: {f.name}")

    print("Generating synthetic retail data (12 datasets)...\n")

    # Phase 1: No dependencies
    print("Phase 1: Independent datasets")
    print(f"  Customers ({N_CUSTOMERS} rows)...")
    customers = generate_customers()

    print(f"  Products ({N_PRODUCTS} rows)...")
    products = generate_products()

    print(f"  Marketing ({N_CAMPAIGNS} campaigns)...")
    marketing = generate_marketing()

    # Phase 2: Depends on Phase 1
    print("\nPhase 2: Session & inventory data")
    print(f"  Sessions ({N_SESSIONS} rows)...")
    sessions = generate_sessions(customers, marketing)

    print(f"  Inventory ({len(products)} rows)...")
    inventory = generate_inventory(products)

    # Phase 3: Depends on Phase 2
    print("\nPhase 3: Event & web analytics data")
    print("  Events (funnel-based per session)...")
    events = generate_events(sessions, products)
    print(f"    ->{len(events)} events generated")

    print(f"  Web Analytics ({N_WEB_EVENTS} events)...")
    web_analytics = generate_web_analytics(sessions, customers)

    # Phase 4: Transactions from converted sessions
    print("\nPhase 4: Transaction data")
    print("  Transactions (from converted sessions)...")
    transactions, txn_session_map = generate_transactions(sessions, products)
    print(f"    ->{len(transactions)} transactions generated")

    # Build transactions_with_session
    txn_session_df = pd.DataFrame(txn_session_map)
    transactions_with_session = transactions.copy()
    if not txn_session_df.empty and not transactions.empty:
        # Map clean order_ids to session_ids
        oid_to_sid = dict(zip(txn_session_df["order_id"], txn_session_df["session_id"]))
        transactions_with_session["session_id"] = transactions_with_session["order_id"].map(
            lambda x: maybe_null(maybe_dirty_str(oid_to_sid.get(str(x).strip(), ""), 0.03))
            if pd.notna(x) else np.nan
        )
    else:
        transactions_with_session["session_id"] = np.nan

    # Backfill total_spend on customers
    if not transactions.empty:
        spend_map = {}
        for _, txn in transactions.iterrows():
            cid = txn.get("customer_id")
            amt = txn.get("total_amount", 0)
            if pd.notna(cid) and pd.notna(amt):
                cid_clean = str(cid).strip().upper()
                spend_map[cid_clean] = spend_map.get(cid_clean, 0) + float(amt)

        customers["total_spend"] = customers["customer_id"].map(
            lambda x: maybe_null(round(spend_map.get(str(x).strip().upper(), 0), 2))
            if pd.notna(x) else 0.0
        )

    # Phase 5: Payments
    print("\nPhase 5: Payment data")
    print(f"  Payments ({len(transactions)} rows)...")
    payments = generate_payments(transactions)

    # Phase 6: Aggregated
    print("\nPhase 6: Aggregated datasets")
    print("  Campaign Performance (daily aggregation)...")
    campaign_performance = generate_campaign_performance(marketing, sessions, transactions_with_session)
    print(f"    ->{len(campaign_performance)} rows generated")

    print("  Funnel Summary (daily aggregation)...")
    funnel_summary = generate_funnel_summary(events, sessions)
    print(f"    ->{len(funnel_summary)} rows generated")

    # All 12 datasets
    datasets = {
        "customers.csv": customers,
        "products.csv": products,
        "marketing.csv": marketing,
        "sessions.csv": sessions,
        "inventory.csv": inventory,
        "events.csv": events,
        "web_analytics.csv": web_analytics,
        "transactions.csv": transactions,
        "transactions_with_session.csv": transactions_with_session,
        "payments.csv": payments,
        "campaign_performance.csv": campaign_performance,
        "funnel_summary.csv": funnel_summary,
    }

    stats = {}
    if local:
        print("\nSaving to local CSV files...")
        for name, df in datasets.items():
            path = RAW_DIR / name
            df.to_csv(path, index=False)
            stats[name] = len(df)
            print(f"  {name:40s} {len(df):>6} rows, {len(df.columns):>3} cols")
        print(f"\nDone! {len(datasets)} files saved to {RAW_DIR}")
    else:
        print("\nSaving to Supabase...")
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from dotenv import load_dotenv as _load_dotenv
        _load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        from db.raw_store import replace_raw_table

        for name, df in datasets.items():
            rows = replace_raw_table(name, df)
            stats[name] = rows
            print(f"  {name:40s} {rows:>6} rows uploaded")
        print(f"\nDone! {len(datasets)} datasets saved to Supabase")

    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate synthetic retail data")
    parser.add_argument(
        "--local", action="store_true",
        help="Write CSVs to data/raw/ instead of Supabase (for debugging)"
    )
    args = parser.parse_args()
    generate_all_data(local=args.local)


if __name__ == "__main__":
    main()
