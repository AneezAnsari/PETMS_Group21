import os
import random
import re
import smtplib
import string
from collections import defaultdict
from datetime import datetime, timedelta 
import base64
import io
import pyotp
import qrcode
from functools import wraps
from email.message import EmailMessage
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-this")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///petms.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])


from email.message import EmailMessage
import smtplib
import os
import re
import requests
import qrcode
from urllib.parse import quote

def get_default_event_image(category):
    category = (category or "General").strip()

    category_images = {
        "Music": "https://images.unsplash.com/photo-1501386761578-eac5c94b800a",
        "Tech": "https://images.unsplash.com/photo-1519389950473-47ba0277781c",
        "Sports": "https://images.unsplash.com/photo-1547347298-4074fc3086f0",
        "Business": "https://images.unsplash.com/photo-1511578314322-379afb476865",
        "Art": "https://images.unsplash.com/photo-1460661419201-fd4cecdf8a8b",
        "Charity": "https://images.unsplash.com/photo-1488521787991-ed7bbaae773c",
        "General": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30",
    }

    return category_images.get(category, category_images["General"])

def fetch_ticketmaster_events(filters):
    api_key = os.environ.get("TICKETMASTER_API_KEY")

    if not api_key:
        raise ValueError("Missing TICKETMASTER_API_KEY in .env")

    params = build_api_event_filters(filters)
    params["apikey"] = api_key

    response = requests.get(
        "https://app.ticketmaster.com/discovery/v2/events.json",
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()

    events = []

    for item in data.get("_embedded", {}).get("events", []):
        venue = item.get("_embedded", {}).get("venues", [{}])[0]

        events.append({
            "title": item.get("name"),
            "description": item.get("info") or item.get("pleaseNote") or "Live event",
            "category": item.get("classifications", [{}])[0].get("segment", {}).get("name", "Other"),
            "location": venue.get("city", {}).get("name", "Unknown"),
            "event_date": item.get("dates", {}).get("start", {}).get("localDate"),
            "event_time": item.get("dates", {}).get("start", {}).get("localTime"),
            "ticketmaster_url": item.get("url"),
        })

    return events
def build_api_event_filters(filters):
    params = {
        "size": 10,
        "sort": "date,asc",
        "countryCode": "CA",
    }

    if filters.get("keyword"):
        params["keyword"] = filters["keyword"]

    if filters.get("location"):
        params["city"] = filters["location"]

    if filters.get("category"):
        params["classificationName"] = filters["category"]

    if filters.get("event_date"):
        # Ticketmaster expects ISO datetime for startDateTime
        params["startDateTime"] = f"{filters['event_date']}T00:00:00Z"

    return params
def fetch_ticketmaster_events(filters):
    api_key = os.environ.get("TICKETMASTER_API_KEY")

    if not api_key:
        raise ValueError("Missing TICKETMASTER_API_KEY in .env")

    params = build_api_event_filters(filters)
    params["apikey"] = api_key

    response = requests.get(
        "https://app.ticketmaster.com/discovery/v2/events.json",
        params=params,
        timeout=10,

    )

    response.raise_for_status()
    data = response.json()

    events = []

    raw_events = data.get("_embedded", {}).get("events", [])

    for item in raw_events:
        venue = item.get("_embedded", {}).get("venues", [{}])[0]
        classifications = item.get("classifications", [{}])
        start_info = item.get("dates", {}).get("start", {})

        events.append({
            "title": item.get("name", "Untitled Event"),
            "description": item.get("info") or item.get("pleaseNote") or "Live event",
            "category": classifications[0].get("segment", {}).get("name", "Other"),
            "location": venue.get("city", {}).get("name", "Unknown"),
            "event_date": start_info.get("localDate", ""),
            "event_time": start_info.get("localTime", ""),
            "ticketmaster_url": item.get("url", "#"),
        })

    return events


def fetch_ticketmaster_events_with_error_handling(filters):
    api_key = os.environ.get("TICKETMASTER_API_KEY")

    if not api_key:
        raise ValueError("Missing TICKETMASTER_API_KEY in .env")

    # Build params using your helper
    params = build_api_event_filters(filters)
    params["apikey"] = api_key

    try:
        response = requests.get(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params=params,
            timeout=10,
        )

        # DEBUG (remove later)
        print("STATUS CODE:", response.status_code)

        response.raise_for_status()
        data = response.json()

    except requests.exceptions.RequestException as e:
        print("REQUEST ERROR:", e)
        raise

    events = []

    raw_events = data.get("_embedded", {}).get("events", [])

    # DEBUG
    print("EVENTS FOUND:", len(raw_events))

    for item in raw_events:
        venue = item.get("_embedded", {}).get("venues", [{}])[0]
        classifications = item.get("classifications", [{}])
        start_info = item.get("dates", {}).get("start", {})

        # safer category handling
        category = "Other"
        if classifications and "segment" in classifications[0]:
            category = classifications[0]["segment"].get("name", "Other")

        events.append({
            "title": item.get("name", "Untitled Event"),
            "description": item.get("info") or item.get("pleaseNote") or "Live event",
            "category": category,
            "location": venue.get("city", {}).get("name", "Unknown"),
            "event_date": start_info.get("localDate", ""),
            "event_time": start_info.get("localTime", ""),
            "ticketmaster_url": item.get("url", "#"),
        })

    return events

def send_email(to_email, subject, body):
    sender_email = os.environ.get("MAIL_USERNAME")
    sender_password = os.environ.get("MAIL_PASSWORD")

    if not sender_email or not sender_password:
        raise ValueError("Missing email credentials from .env")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("MAIL_FROM")
    msg["To"] = to_email
    msg.set_content(body)

    mail_server = os.environ.get("MAIL_SERVER")
    mail_port = int(os.environ.get("MAIL_PORT"))
    use_ssl = os.environ.get("MAIL_USE_SSL") == "True"
    use_tls = os.environ.get("MAIL_USE_TLS") == "True"

    if use_ssl:
        with smtplib.SMTP_SSL(mail_server, mail_port) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(mail_server, mail_port) as smtp:
            if use_tls:
                smtp.starttls()
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
            
def generate_ticket_code():
    return "PETMS-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def generate_ticket_qr_base64(ticket_code):
    verification_url = url_for("verify_ticket", ticket_code=ticket_code, _external=True)

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )
    qr.add_data(verification_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return qr_base64          


def generate_ticket_code():
    return "PETMS-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def redirect_after_login(user):
    if user.role == "admin":
        return redirect(url_for("admin_dashboard"))
    if user.role == "organizer":
        return redirect(url_for("organizer_dashboard"))
    return redirect(url_for("events"))


def get_2fa_qr_data_uri(user):
    if not user.twofa_secret:
        return None
    totp = pyotp.TOTP(user.twofa_secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="PETMS")
    img = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if current_user.role != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("home"))
        return view_func(*args, **kwargs)

    return wrapped


def organizer_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if current_user.role != "organizer":
            flash("Organizer access required.", "error")
            return redirect(url_for("home"))
        organizer = Organizer.query.filter_by(user_id=current_user.id).first()
        if not organizer:
            flash("No organizer profile is linked to this account.", "error")
            return redirect(url_for("home"))
        return view_func(*args, **kwargs)

    return wrapped
def parse_natural_language_query(text):
    text = (text or "").strip().lower()

    filters = {
        "keyword": "",
        "category": "",
        "location": "",
        "event_date": "",
        "event_time": "",
        "max_price": "",
    }

    category_map = {
        "music": "Music",
        "concert": "Music",
        "show": "Music",
        "tech": "Tech",
        "technology": "Tech",
        "ai": "Tech",
        "sports": "Sports",
        "sport": "Sports",
        "game": "Sports",
        "business": "Business",
        "networking": "Business",
        "art": "Art",
        "gallery": "Art",
        "charity": "Charity",
        "fundraiser": "Charity",
    }

    known_locations = [
        "toronto",
        "mississauga",
        "brampton",
        "north york",
        "scarborough",
    ]

    for word, mapped_category in category_map.items():
        if word in text:
            filters["category"] = mapped_category
            break

    for loc in known_locations:
        if loc in text:
            filters["location"] = loc.title()
            break

    if "cheap" in text or "budget" in text or "low cost" in text:
        filters["max_price"] = "50"
    elif "free" in text:
        filters["max_price"] = "0"

    today = datetime.now().date()

    if "today" in text:
        filters["event_date"] = today.strftime("%Y-%m-%d")
    elif "tomorrow" in text:
        filters["event_date"] = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    elif "this weekend" in text or "weekend" in text:
        days_until_saturday = (5 - today.weekday()) % 7
        saturday = today + timedelta(days=days_until_saturday)
        filters["event_date"] = saturday.strftime("%Y-%m-%d")
    elif "next week" in text:
        filters["event_date"] = (today + timedelta(days=7)).strftime("%Y-%m-%d")

    if "morning" in text:
        filters["event_time"] = "09:00"
    elif "afternoon" in text:
        filters["event_time"] = "13:00"
    elif "evening" in text or "night" in text:
        filters["event_time"] = "18:00"

    match_12hr = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
    match_24hr = re.search(r"\b(\d{1,2}):(\d{2})\b", text)

    if match_12hr:
        hour = int(match_12hr.group(1))
        minute = int(match_12hr.group(2) or 0)
        meridian = match_12hr.group(3)

        if meridian == "pm" and hour != 12:
            hour += 12
        if meridian == "am" and hour == 12:
            hour = 0

        filters["event_time"] = f"{hour:02d}:{minute:02d}"
    elif match_24hr:
        hour = int(match_24hr.group(1))
        minute = int(match_24hr.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            filters["event_time"] = f"{hour:02d}:{minute:02d}"

    ignore_words = {
        "cheap", "free", "budget", "music", "concert", "show", "tech", "technology", "ai",
        "sports", "sport", "game", "business", "networking", "art", "gallery",
        "charity", "fundraiser", "today", "tomorrow", "weekend", "this", "next",
        "week", "morning", "afternoon", "evening", "night",
        "in", "at", "on", "after", "before", "events", "event"
    }

    leftover = []
    for token in re.findall(r"[a-zA-Z]+", text):
        if token not in ignore_words and token not in {"toronto", "mississauga", "brampton", "north", "york", "scarborough"}:
            leftover.append(token)

    if leftover:
        filters["keyword"] = " ".join(leftover)

    return filters
def apply_internal_event_filters(query, filters):
    if filters.get("keyword"):
        query = query.filter(
            Event.title.ilike(f"%{filters['keyword']}%") |
            Event.description.ilike(f"%{filters['keyword']}%")
        )

    if filters.get("category"):
        query = query.filter(Event.category == filters["category"])

    if filters.get("location"):
        query = query.filter(Event.location.ilike(f"%{filters['location']}%"))

    if filters.get("event_date"):
        try:
            selected_date = datetime.strptime(filters["event_date"], "%Y-%m-%d").date()
            query = query.filter(db.func.date(Event.event_date) == selected_date)
        except ValueError:
            pass

    if filters.get("event_time"):
        try:
            selected_time = datetime.strptime(filters["event_time"], "%H:%M").time()
            query = query.filter(db.func.time(Event.event_date) >= selected_time)
        except ValueError:
            pass

    if filters.get("max_price"):
        try:
            query = query.filter(Event.ticket_price <= float(filters["max_price"]))
        except ValueError:
            pass

    return query

def build_api_event_filters(filters):
    params = {}

    if filters.get("keyword"):
        params["keyword"] = filters["keyword"]

    if filters.get("location"):
        params["city"] = filters["location"]

    if filters.get("event_date"):
        params["event_date"] = filters["event_date"]

    if filters.get("event_time"):
        params["event_time"] = filters["event_time"]

    if filters.get("category"):
        params["category"] = filters["category"]

    if filters.get("max_price"):
        params["max_price"] = filters["max_price"]

    return params

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="customer")
    twofa_enabled = db.Column(db.Boolean, default=False)
    twofa_secret = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", backref="user", lazy=True, cascade="all, delete-orphan")
    organizer_profile = db.relationship("Organizer", backref="user", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Organizer(db.Model):
    __tablename__ = "organizers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(25))
    organization_name = db.Column(db.String(150))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    events = db.relationship("Event", backref="organizer", lazy=True, cascade="all, delete-orphan")


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey("organizers.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), default="General")
    location = db.Column(db.String(150), nullable=False)
    event_date = db.Column(db.DateTime, nullable=False)
    ticket_price = db.Column(db.Float, nullable=False)
    available_tickets = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image_url = db.Column(db.String(500))
    bookings = db.relationship("Booking", backref="event", lazy=True, cascade="all, delete-orphan")


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="confirmed")
    booked_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)

    tickets = db.relationship("Ticket", backref="booking", lazy=True, cascade="all, delete-orphan")


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    ticket_code = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default="valid")
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def get_organizer_for_current_user():
    return Organizer.query.filter_by(user_id=current_user.id).first()


def build_platform_analytics():
    organizers = Organizer.query.order_by(Organizer.organization_name.asc()).all()
    events = Event.query.order_by(Event.event_date.asc()).all()
    bookings = Booking.query.order_by(Booking.booked_at.asc()).all()

    organizer_count = len(organizers)
    event_count = len(events)
    booking_count = len(bookings)
    ticket_count = sum(len(booking.tickets) for booking in bookings)
    total_revenue = sum(booking.total_price for booking in bookings)

    bookings_per_event = []
    for event in events:
        tickets_sold = sum(booking.quantity for booking in event.bookings if booking.status == "confirmed")
        bookings_per_event.append({"label": event.title, "value": tickets_sold})

    revenue_by_organizer = []
    for organizer in organizers:
        organizer_revenue = 0
        for event in organizer.events:
            organizer_revenue += sum(booking.total_price for booking in event.bookings if booking.status == "confirmed")
        revenue_by_organizer.append({
            "label": organizer.organization_name or organizer.name,
            "value": round(organizer_revenue, 2),
        })

    monthly = defaultdict(float)
    for booking in bookings:
        label = booking.booked_at.strftime("%Y-%m")
        monthly[label] += booking.total_price
    revenue_over_time = [{"label": key, "value": round(value, 2)} for key, value in sorted(monthly.items())]

    return {
        "organizer_count": organizer_count,
        "event_count": event_count,
        "booking_count": booking_count,
        "ticket_count": ticket_count,
        "total_revenue": round(total_revenue, 2),
        "bookings_per_event": bookings_per_event,
        "revenue_by_organizer": revenue_by_organizer,
        "revenue_over_time": revenue_over_time,
    }


def build_organizer_analytics(organizer):
    events = Event.query.filter_by(organizer_id=organizer.id).order_by(Event.event_date.asc()).all()
    bookings = (
        Booking.query.join(Event)
        .filter(Event.organizer_id == organizer.id)
        .order_by(Booking.booked_at.asc())
        .all()
    )

    event_count = len(events)
    booking_count = len(bookings)
    ticket_count = sum(booking.quantity for booking in bookings if booking.status == "confirmed")
    total_revenue = round(sum(booking.total_price for booking in bookings if booking.status == "confirmed"), 2)

    bookings_per_event = []
    for event in events:
        sold = sum(booking.quantity for booking in event.bookings if booking.status == "confirmed")
        bookings_per_event.append({"label": event.title, "value": sold})

    revenue_per_event = []
    for event in events:
        revenue = round(sum(booking.total_price for booking in event.bookings if booking.status == "confirmed"), 2)
        revenue_per_event.append({"label": event.title, "value": revenue})

    monthly = defaultdict(float)
    for booking in bookings:
        label = booking.booked_at.strftime("%Y-%m")
        monthly[label] += booking.total_price
    revenue_over_time = [{"label": key, "value": round(value, 2)} for key, value in sorted(monthly.items())]

    top_event = None
    if bookings_per_event:
        top_event = max(bookings_per_event, key=lambda item: item["value"])

    return {
        "organizer": organizer,
        "event_count": event_count,
        "booking_count": booking_count,
        "ticket_count": ticket_count,
        "total_revenue": total_revenue,
        "bookings_per_event": bookings_per_event,
        "revenue_per_event": revenue_per_event,
        "revenue_over_time": revenue_over_time,
        "top_event": top_event,
        "events": events,
    }


@app.route("/")
def home():
    featured_events = Event.query.order_by(Event.event_date.asc()).limit(6).all()
    return render_template("index.html", featured_events=featured_events)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered.", "error")
            return redirect(url_for("register"))

        new_user = User(username=username, email=email, role="customer")
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if user.twofa_enabled and user.twofa_secret:
                session["pre_2fa_user_id"] = user.id
                flash("Enter your 2FA code to finish signing in.", "success")
                return redirect(url_for("verify_2fa_login"))

            login_user(user)
            flash("Logged in successfully.", "success")
            return redirect_after_login(user)

        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.pop("pre_2fa_user_id", None)
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/account-security")
@login_required
def account_security():
    qr_code_data = None
    if current_user.twofa_secret:
        qr_code_data = get_2fa_qr_data_uri(current_user)
    return render_template("account_security.html", qr_code_data=qr_code_data)


@app.route("/setup-2fa", methods=["GET", "POST"])
@login_required
def setup_2fa():
    if not current_user.twofa_secret:
        current_user.twofa_secret = pyotp.random_base32()
        db.session.commit()

    totp = pyotp.TOTP(current_user.twofa_secret)
    provisioning_uri = totp.provisioning_uri(name=current_user.email, issuer_name="PETMS")
    qr_code_data = get_2fa_qr_data_uri(current_user)

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if totp.verify(code, valid_window=1):
            current_user.twofa_enabled = True
            db.session.commit()
            flash("Two-factor authentication enabled.", "success")
            return redirect(url_for("account_security"))

        flash("Invalid 2FA code. Try again.", "error")

    return render_template(
        "setup_2fa.html",
        qr_code_data=qr_code_data,
        manual_secret=current_user.twofa_secret,
        provisioning_uri=provisioning_uri,
    )


@app.route("/disable-2fa", methods=["POST"])
@login_required
def disable_2fa():
    current_user.twofa_enabled = False
    current_user.twofa_secret = None
    db.session.commit()
    flash("Two-factor authentication disabled.", "success")
    return redirect(url_for("account_security"))


@app.route("/verify-2fa-login", methods=["GET", "POST"])
def verify_2fa_login():
    pending_user_id = session.get("pre_2fa_user_id")
    if not pending_user_id:
        flash("Your sign-in session expired. Please log in again.", "error")
        return redirect(url_for("login"))

    user = db.session.get(User, pending_user_id)
    if not user or not user.twofa_secret:
        session.pop("pre_2fa_user_id", None)
        flash("Unable to verify 2FA for this account.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        totp = pyotp.TOTP(user.twofa_secret)
        if totp.verify(code, valid_window=1):
            session.pop("pre_2fa_user_id", None)
            login_user(user)
            flash("Two-factor verification successful.", "success")
            return redirect_after_login(user)

        flash("Invalid 2FA code.", "error")

    return render_template("verify_2fa_login.html", email=user.email)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            token = serializer.dumps(user.email, salt="password-reset")
            reset_link = url_for("reset_password", token=token, _external=True)
            body = f"""Hello {user.username},

You requested a password reset for your PETMS account.

Click the link below to reset your password:
{reset_link}

If you did not request this, you can ignore this email.
"""
            try:
                send_email(user.email, "PETMS Password Reset", body)
            except Exception as exc:
                flash(f"Email failed to send: {exc}", "error")
                return redirect(url_for("forgot_password"))

        flash("If that email exists, a reset link has been sent.", "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = serializer.loads(token, salt="password-reset", max_age=3600)
    except SignatureExpired:
        flash("This reset link has expired.", "error")
        return redirect(url_for("forgot_password"))
    except BadSignature:
        flash("Invalid reset link.", "error")
        return redirect(url_for("forgot_password"))

    user = User.query.filter_by(email=email).first_or_404()

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("reset_password", token=token))

        user.set_password(password)
        db.session.commit()
        flash("Password updated successfully. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html")



@app.route("/events")
def events():
    search_text = request.args.get("search_text", "").strip()
    search_mode = request.args.get("search_mode", "normal").strip()

    filters = {
        "keyword": "",
        "category": request.args.get("category", "").strip(),
        "location": request.args.get("location", "").strip(),
        "event_date": request.args.get("event_date", "").strip(),
        "event_time": request.args.get("event_time", "").strip(),
        "max_price": request.args.get("max_price", "").strip(),
    }

    if search_text:
        if search_mode == "smart":
            parsed_filters = parse_natural_language_query(search_text)

            for key in filters:
                if not filters[key] and parsed_filters.get(key):
                    filters[key] = parsed_filters[key]
        else:
            filters["keyword"] = search_text

    query = Event.query
    query = apply_internal_event_filters(query, filters)
    all_events = query.order_by(Event.event_date.asc()).all()

    categories = [
        row[0]
        for row in db.session.query(Event.category).distinct().order_by(Event.category).all()
        if row[0]
    ]

    return render_template(
        "events.html",
        events=all_events,
        categories=categories,
        filters={
            **filters,
            "search_text": search_text,
            "search_mode": search_mode,
        }
    )
@app.route("/test-api")
def test_api():
    filters = {
        "keyword": "music",
        "category": "",
        "location": "Toronto",
        "event_date": "",
        "event_time": "",
        "max_price": "",
    }

    events = fetch_ticketmaster_events(filters)
    return {"count": len(events), "events": events[:3]}

@app.route("/real-events")
def real_events():
    search_text = request.args.get("search_text", "").strip()
    search_mode = request.args.get("search_mode", "normal").strip()

    filters = {
        "keyword": "",
        "category": request.args.get("category", "").strip(),
        "location": request.args.get("location", "").strip(),
        "event_date": request.args.get("event_date", "").strip(),
        "event_time": request.args.get("event_time", "").strip(),
        "max_price": request.args.get("max_price", "").strip(),
    }

    if search_text:
        if search_mode == "smart":
            parsed_filters = parse_natural_language_query(search_text)
            for key in filters:
                if not filters[key] and parsed_filters.get(key):
                    filters[key] = parsed_filters[key]
        else:
            filters["keyword"] = search_text

    try:
        events = fetch_ticketmaster_events(filters)
    except Exception as e:
        flash(f"Unable to load live events: {e}", "error")
        events = []

    categories = ["Music", "Sports", "Tech", "Business", "Art", "Charity"]

    return render_template(
        "real_events.html",
        events=events,
        categories=categories,
        filters={
            **filters,
            "search_text": search_text,
            "search_mode": search_mode,
        }
    )
 
@app.route("/book/<int:event_id>", methods=["GET", "POST"])
@login_required
def book_ticket(event_id):
    event = Event.query.get_or_404(event_id)

    if request.method == "POST":
        quantity = int(request.form.get("quantity", 1))
        if quantity <= 0:
            flash("Quantity must be greater than 0.", "error")
            return redirect(url_for("book_ticket", event_id=event.id))
        if quantity > event.available_tickets:
            flash("Not enough tickets available.", "error")
            return redirect(url_for("book_ticket", event_id=event.id))

        total_price = quantity * event.ticket_price
        booking = Booking(quantity=quantity, total_price=total_price, user_id=current_user.id, event_id=event.id)
        event.available_tickets -= quantity
        db.session.add(booking)
        db.session.commit()

        created_tickets = []
        for _ in range(quantity):
            ticket = Ticket(booking_id=booking.id, ticket_code=generate_ticket_code())
            db.session.add(ticket)
            created_tickets.append(ticket)
        db.session.commit()

        ticket_lines = "\n".join(f"- {ticket.ticket_code}" for ticket in created_tickets)
        view_tickets_link = url_for("my_tickets", _external=True)
        body = f"""Hello {current_user.username},

Your booking is confirmed.

Event: {event.title}
Organizer: {event.organizer.organization_name or event.organizer.name}
Location: {event.location}
Date: {event.event_date.strftime('%Y-%m-%d %H:%M')}
Quantity: {quantity}
Total Price: ${total_price:.2f}

Your Digital Ticket Code(s):
{ticket_lines}

You can also view your tickets here:
{view_tickets_link}

Please keep this email for entry reference.
"""
        try:
            send_email(current_user.email, "Your PETMS Digital Ticket", body)
            flash("Booking successful. Your digital ticket has been emailed.", "success")
        except Exception as exc:
            flash(f"Booking saved, but email failed: {exc}", "error")

        return redirect(url_for("my_bookings"))

    return render_template("book_ticket.html", event=event)


@app.route("/my-bookings")
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booked_at.desc()).all()
    return render_template("my_bookings.html", bookings=bookings)


@app.route("/my-tickets")
@login_required
def my_tickets():
    tickets = Ticket.query.join(Booking).filter(Booking.user_id == current_user.id).order_by(Ticket.issued_at.desc()).all()
    return render_template("my_tickets.html", tickets=tickets)


@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    analytics = build_platform_analytics()
    return render_template("admin_dashboard.html", **analytics)


@app.route("/admin/reports")
@login_required
@admin_required
def admin_reports():
    analytics = build_platform_analytics()
    return render_template("admin_reports.html", **analytics)


@app.route("/organizer")
@login_required
@organizer_required
def organizer_dashboard():
    organizer = get_organizer_for_current_user()
    analytics = build_organizer_analytics(organizer)
    return render_template("organizer_dashboard.html", **analytics)


@app.route("/organizer/reports")
@login_required
@organizer_required
def organizer_reports():
    organizer = get_organizer_for_current_user()
    analytics = build_organizer_analytics(organizer)
    return render_template("organizer_reports.html", **analytics)


@app.route("/admin/organizers")
@login_required
@admin_required
def admin_organizers():
    organizers = Organizer.query.order_by(Organizer.created_at.desc()).all()
    return render_template("admin_organizers.html", organizers=organizers)


@app.route("/admin/organizers/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_organizer():
    if request.method == "POST":
        account_email = request.form.get("account_email", "").strip().lower()
        account_username = request.form.get("account_username", "").strip()
        account_password = request.form.get("account_password", "").strip()

        if User.query.filter_by(email=account_email).first():
            flash("That organizer account email is already in use.", "error")
            return redirect(url_for("create_organizer"))

        user = User(username=account_username, email=account_email, role="organizer")
        user.set_password(account_password)
        db.session.add(user)
        db.session.flush()

        organizer = Organizer(
            user_id=user.id,
            name=request.form.get("name", "").strip(),
            email=request.form.get("email", "").strip(),
            phone=request.form.get("phone", "").strip(),
            organization_name=request.form.get("organization_name", "").strip(),
            description=request.form.get("description", "").strip(),
        )
        db.session.add(organizer)
        db.session.commit()
        flash("Organizer created successfully.", "success")
        return redirect(url_for("admin_organizers"))

    return render_template("admin_organizer_form.html", organizer=None)


@app.route("/admin/organizers/<int:organizer_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_organizer(organizer_id):
    organizer = Organizer.query.get_or_404(organizer_id)
    if request.method == "POST":
        organizer.name = request.form.get("name", "").strip()
        organizer.email = request.form.get("email", "").strip()
        organizer.phone = request.form.get("phone", "").strip()
        organizer.organization_name = request.form.get("organization_name", "").strip()
        organizer.description = request.form.get("description", "").strip()
        organizer.user.username = request.form.get("account_username", "").strip() or organizer.user.username
        new_account_email = request.form.get("account_email", "").strip().lower()
        existing = User.query.filter(User.email == new_account_email, User.id != organizer.user.id).first()
        if existing:
            flash("That organizer account email is already in use.", "error")
            return redirect(url_for("edit_organizer", organizer_id=organizer.id))
        organizer.user.email = new_account_email or organizer.user.email
        new_password = request.form.get("account_password", "").strip()
        if new_password:
            organizer.user.set_password(new_password)
        db.session.commit()
        flash("Organizer updated successfully.", "success")
        return redirect(url_for("admin_organizers"))

    return render_template("admin_organizer_form.html", organizer=organizer)


@app.route("/admin/organizers/<int:organizer_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_organizer(organizer_id):
    organizer = Organizer.query.get_or_404(organizer_id)
    if organizer.events:
        flash("Cannot delete organizer with existing events.", "error")
        return redirect(url_for("admin_organizers"))
    organizer_user = organizer.user
    db.session.delete(organizer)
    if organizer_user:
        db.session.delete(organizer_user)
    db.session.commit()
    flash("Organizer deleted successfully.", "success")
    return redirect(url_for("admin_organizers"))


@app.route("/admin/events")
@login_required
@admin_required
def admin_events():
    events = Event.query.order_by(Event.event_date.asc()).all()
    return render_template("admin_events.html", events=events)


@app.route("/admin/events/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_event():
    organizers = Organizer.query.order_by(Organizer.organization_name.asc(), Organizer.name.asc()).all()

    if request.method == "POST":
        category = request.form.get("category", "").strip() or "General"
        image_url = request.form.get("image_url", "").strip()

        event = Event(
            organizer_id=int(request.form.get("organizer_id")),
            title=request.form.get("title", "").strip(),
            description=request.form.get("description", "").strip(),
            category=category,
            location=request.form.get("location", "").strip(),
            event_date=datetime.strptime(request.form.get("event_date"), "%Y-%m-%dT%H:%M"),
            ticket_price=float(request.form.get("ticket_price")),
            available_tickets=int(request.form.get("available_tickets")),
            image_url=image_url if image_url else get_default_event_image(category),
        )

        db.session.add(event)
        db.session.commit()
        flash("Event created successfully.", "success")
        return redirect(url_for("admin_events"))

    return render_template("admin_event_form.html", event=None, organizers=organizers)


@app.route("/admin/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    organizers = Organizer.query.order_by(Organizer.organization_name.asc(), Organizer.name.asc()).all()

    if request.method == "POST":
        event.organizer_id = int(request.form.get("organizer_id"))
        event.title = request.form.get("title", "").strip()
        event.description = request.form.get("description", "").strip()
        event.category = request.form.get("category", "").strip() or "General"
        event.location = request.form.get("location", "").strip()
        event.event_date = datetime.strptime(request.form.get("event_date"), "%Y-%m-%dT%H:%M")
        event.ticket_price = float(request.form.get("ticket_price"))
        event.available_tickets = int(request.form.get("available_tickets"))

        event.image_url = request.form.get("image_url", "").strip()

        db.session.commit()
        flash("Event updated successfully.", "success")
        return redirect(url_for("admin_events"))

    return render_template("admin_event_form.html", event=event, organizers=organizers)

@app.route("/admin/events/<int:event_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted successfully.", "success")
    return redirect(url_for("admin_events"))


@app.route("/seed-admin")
def seed_admin():
    existing_admin = User.query.filter_by(email="admin@petms.com").first()
    if existing_admin:
        return "Admin already exists."
    admin = User(username="Admin", email="admin@petms.com", role="admin")
    admin.set_password("Admin123!")
    db.session.add(admin)
    db.session.commit()
    return "Admin created."


@app.route("/seed-organizers")
def seed_organizers():
    if Organizer.query.count() > 0:
        return "Organizers already exist."

    organizer_seed = [
        {
            "account_username": "livenorth",
            "account_email": "organizer1@petms.com",
            "account_password": "Organizer123!",
            "name": "Lena Cruz",
            "email": "lena@livenorth.ca",
            "phone": "416-555-1010",
            "organization_name": "Live North Events",
            "description": "Runs concerts, nightlife showcases, and city festival programming.",
        },
        {
            "account_username": "futureforge",
            "account_email": "organizer2@petms.com",
            "account_password": "Organizer123!",
            "name": "Marcus Hall",
            "email": "marcus@futureforge.io",
            "phone": "416-555-2020",
            "organization_name": "Future Forge",
            "description": "Hosts tech conferences, startup meetups, and AI demo nights.",
        },
        {
            "account_username": "communitypulse",
            "account_email": "organizer3@petms.com",
            "account_password": "Organizer123!",
            "name": "Priya Raman",
            "email": "priya@communitypulse.org",
            "phone": "905-555-3030",
            "organization_name": "Community Pulse",
            "description": "Organizes charity galas, local wellness drives, and youth fundraisers.",
        },
        {
            "account_username": "grandstand",
            "account_email": "organizer4@petms.com",
            "account_password": "Organizer123!",
            "name": "Jordan Price",
            "email": "jordan@grandstandsports.ca",
            "phone": "905-555-4040",
            "organization_name": "Grandstand Sports",
            "description": "Specializes in live sports nights, fan events, and fitness showcases.",
        },
        {
            "account_username": "northgallery",
            "account_email": "organizer5@petms.com",
            "account_password": "Organizer123!",
            "name": "Ava Kim",
            "email": "ava@northgallery.art",
            "phone": "647-555-5050",
            "organization_name": "North Gallery Collective",
            "description": "Curates gallery openings, public art walks, and design exhibitions.",
        },
        {
            "account_username": "summitworks",
            "account_email": "organizer6@petms.com",
            "account_password": "Organizer123!",
            "name": "Noah Bennett",
            "email": "noah@summitworks.biz",
            "phone": "647-555-6060",
            "organization_name": "SummitWorks Events",
            "description": "Runs networking sessions, founder summits, and professional workshops.",
        },
    ]

    for item in organizer_seed:
        user = User(username=item["account_username"], email=item["account_email"], role="organizer")
        user.set_password(item["account_password"])
        db.session.add(user)
        db.session.flush()

        organizer = Organizer(
            user_id=user.id,
            name=item["name"],
            email=item["email"],
            phone=item["phone"],
            organization_name=item["organization_name"],
            description=item["description"],
        )
        db.session.add(organizer)

    db.session.commit()
    return "6 organizers seeded. Organizer login password: Organizer123!"


@app.route("/seed-events")
def seed_events():
    if Event.query.count() > 0:
        return "Events already exist."

    organizers = {org.organization_name: org for org in Organizer.query.all()}
    if not organizers:
        return "Please seed organizers first."

    event_data = [
        ("Live North Events", "Toronto Jazz After Dark", "Music", "Downtown Toronto Hall", datetime(2026, 4, 10, 19, 0), 45.0, 180, "A late-evening jazz showcase featuring four local ensembles and a rooftop lounge set."),
        ("Live North Events", "Queen Street Indie Fest", "Music", "Queen Street Warehouse", datetime(2026, 4, 19, 18, 30), 35.0, 220, "An indie lineup with food vendors, merch booths, and an acoustic side stage."),
        ("Live North Events", "Harbourfront Summer Beats", "Music", "Toronto Harbourfront Stage", datetime(2026, 5, 2, 17, 0), 55.0, 300, "An outdoor waterfront concert with electronic, pop, and dance acts."),
        ("Live North Events", "Midtown Comedy and Music Night", "Music", "North York Arts Theatre", datetime(2026, 5, 16, 20, 0), 28.0, 140, "A mixed-format night with stand-up, live vocals, and crowd games."),
        ("Live North Events", "Brampton Block Party Live", "Music", "Brampton Civic Square", datetime(2026, 6, 6, 16, 0), 20.0, 400, "A city block party with DJs, local rappers, and late-night food trucks."),
        ("Future Forge", "AI Builder Summit Toronto", "Tech", "Metro Toronto Convention Centre", datetime(2026, 4, 14, 9, 0), 149.0, 260, "A full-day summit for builders shipping products with AI and automation."),
        ("Future Forge", "Startup MVP Sprint", "Tech", "Mississauga Innovation Hub", datetime(2026, 4, 28, 10, 0), 65.0, 120, "Hands-on startup sprint focused on prototyping, validation, and launch planning."),
        ("Future Forge", "Cloud Architecture Workshop", "Tech", "Brampton Tech Lab", datetime(2026, 5, 9, 11, 0), 79.0, 90, "Workshop on deployment, databases, observability, and production workflows."),
        ("Future Forge", "Women in Product Meetup", "Tech", "Downtown Toronto Hall", datetime(2026, 5, 21, 18, 0), 18.0, 130, "Community meetup focused on product strategy, career growth, and mentoring."),
        ("Future Forge", "Hack Northside Mini Hackathon", "Tech", "North York Civic Centre", datetime(2026, 6, 12, 8, 30), 25.0, 200, "A mini hackathon for students and juniors building software over one weekend."),
        ("Community Pulse", "Spring Fundraiser Gala", "Charity", "Mississauga Convention Centre", datetime(2026, 4, 22, 19, 0), 95.0, 160, "Formal gala dinner raising funds for youth mental health programs."),
        ("Community Pulse", "Neighbourhood Wellness Fair", "Charity", "Scarborough Community Hall", datetime(2026, 4, 26, 10, 0), 0.0, 260, "Free public fair with wellness booths, screenings, and local services."),
        ("Community Pulse", "Food Drive Volunteer Day", "Charity", "Brampton Civic Square", datetime(2026, 5, 3, 9, 30), 0.0, 180, "A volunteer and donation day supporting regional food bank partners."),
        ("Community Pulse", "Youth Leaders Breakfast", "Business", "Downtown Toronto Hall", datetime(2026, 5, 27, 8, 0), 22.0, 110, "Breakfast session for student leaders, non-profits, and community coordinators."),
        ("Community Pulse", "Community Run for Change", "Charity", "Etobicoke Lakeshore Park", datetime(2026, 6, 20, 7, 30), 30.0, 350, "A 5K run and fundraiser with family programming and sponsor booths."),
        ("Grandstand Sports", "Downtown Hoops Showcase", "Sports", "North York Stadium", datetime(2026, 4, 18, 18, 0), 38.0, 240, "Showcase game night with halftime contests and premium courtside upgrades."),
        ("Grandstand Sports", "Mississauga Amateur Fight Night", "Sports", "Mississauga Event Arena", datetime(2026, 5, 1, 19, 30), 72.0, 180, "A local fight card featuring amateur kickboxing and boxing bouts."),
        ("Grandstand Sports", "Soccer Skills Open Day", "Sports", "Brampton Sports Dome", datetime(2026, 5, 17, 13, 0), 15.0, 150, "Open training sessions, skills stations, and youth coaching clinics."),
        ("Grandstand Sports", "Fitness Expo Live", "Sports", "Metro Toronto Convention Centre", datetime(2026, 6, 5, 10, 0), 48.0, 280, "Fitness brands, seminars, live demos, and strength sport mini-events."),
        ("Grandstand Sports", "Scarborough Night Run", "Sports", "Scarborough Waterfront Trail", datetime(2026, 6, 27, 20, 0), 25.0, 320, "Night run event with medals, hydration stations, and local vendors."),
        ("North Gallery Collective", "Toronto Photo Week Opening", "Art", "Queen Street Gallery", datetime(2026, 4, 12, 18, 0), 18.0, 130, "An opening night for a contemporary photography exhibition with artist talks."),
        ("North Gallery Collective", "Design Market and Print Fair", "Art", "Stackt Market Toronto", datetime(2026, 4, 25, 11, 0), 12.0, 200, "Independent artists, print makers, and design vendors in a weekend market."),
        ("North Gallery Collective", "Public Art Walk North York", "Art", "North York Civic Centre", datetime(2026, 5, 8, 14, 0), 0.0, 150, "Guided public art walk highlighting murals and installations in North York."),
        ("North Gallery Collective", "Summer Gallery Night", "Art", "Downtown Toronto Hall", datetime(2026, 6, 11, 18, 30), 24.0, 170, "Extended evening gallery hours with talks, drinks, and live sketch sessions."),
        ("North Gallery Collective", "Digital Illustration Jam", "Art", "Mississauga Innovation Hub", datetime(2026, 6, 21, 12, 0), 30.0, 100, "Collaborative illustration sessions, talks, and portfolio reviews."),
        ("SummitWorks Events", "Founder Networking Breakfast", "Business", "Toronto Financial District Lounge", datetime(2026, 4, 16, 8, 0), 32.0, 90, "Morning networking for startup founders, operators, and early-stage investors."),
        ("SummitWorks Events", "Leadership in Action Forum", "Business", "Downtown Toronto Hall", datetime(2026, 5, 6, 9, 30), 88.0, 140, "Panels and workshops focused on leadership, team building, and scale-up systems."),
        ("SummitWorks Events", "Sales Accelerator Masterclass", "Business", "Mississauga Convention Centre", datetime(2026, 5, 19, 13, 0), 54.0, 110, "Masterclass covering pipeline building, demos, and B2B sales strategy."),
        ("SummitWorks Events", "Creator Economy Meetup", "Business", "Brampton Tech Lab", datetime(2026, 6, 3, 18, 0), 20.0, 160, "Meetup for creators, brand strategists, and digital entrepreneurs."),
        ("SummitWorks Events", "Career Switch Bootcamp", "Business", "Scarborough Community Hall", datetime(2026, 6, 18, 10, 0), 40.0, 130, "Bootcamp for professionals moving into product, tech, and business roles."),
    ]

    events = []
    for organizer_name, title, category, location, event_date, ticket_price, available_tickets, description in event_data:
        organizer = organizers[organizer_name]
        events.append(
            Event(
                organizer_id=organizer.id,
                title=title,
                description=description,
                category=category,
                location=location,
                event_date=event_date,
                ticket_price=ticket_price,
                available_tickets=available_tickets,
            )
        )

    db.session.add_all(events)
    db.session.commit()
    return f"{len(events)} realistic events seeded."

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)

@app.route("/verify-ticket/<ticket_code>")
def verify_ticket(ticket_code):
    ticket = Ticket.query.filter_by(ticket_code=ticket_code).first()

    if not ticket:
        return render_template("ticket_verification.html", valid=False, ticket=None)

    return render_template("ticket_verification.html", valid=True, ticket=ticket)

@app.route("/my-ticket/<ticket_code>")
@login_required
def my_ticket(ticket_code):
    ticket = Ticket.query.filter_by(ticket_code=ticket_code).first_or_404()
    qr_code_base64 = generate_ticket_qr_base64(ticket.ticket_code)
    return render_template("my_ticket.html", ticket=ticket, qr_code_base64=qr_code_base64)
