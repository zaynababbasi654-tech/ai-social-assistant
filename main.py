import sqlite3
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="TechClues Social AI")

DB_NAME = "customers.db"

WEBSITE = "https://techclues.co.uk/"
BOOKING_LINK = (
    "https://api.leadconnectorhq.com/widget/booking/"
    "3OD65zni7fQ51wVWzKny"
)
PHONE = "+44-7472-411699"
EMAIL = "info@techclues.co.uk"

SERVICES = {
    "Website Development":
        "https://techclues.co.uk/website-development",
    "Digital Marketing":
        "https://techclues.co.uk/digital-marketing",
    "AI Services":
        "https://techclues.co.uk/ai-services",
    "Mobile App Development": WEBSITE,
    "Software Development": WEBSITE,
    "Web 3.0 & Blockchain": WEBSITE,
    "Penetration Testing": WEBSITE,
    "Web Security": WEBSITE,
    "SEO": WEBSITE,
    "Communication & Support": WEBSITE,
    "DevOps Services": WEBSITE,
}


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                sender_id TEXT PRIMARY KEY,
                platform TEXT,
                full_name TEXT,
                phone TEXT,
                email TEXT,
                service TEXT,
                enquiry_type TEXT,
                notes TEXT,
                booking_status TEXT DEFAULT 'not booked',
                created_at TEXT
            )
        """)


init_db()


class IncomingMessage(BaseModel):
    sender_id: str
    message: str
    platform: str = "test"


def get_customer(sender_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM customers WHERE sender_id = ?",
            (sender_id,)
        ).fetchone()
        return dict(row) if row else None


def save_customer(sender_id, platform, **fields):
    current = get_customer(sender_id) or {}

    data = {
        "platform": platform,
        "full_name": current.get("full_name"),
        "phone": current.get("phone"),
        "email": current.get("email"),
        "service": current.get("service"),
        "enquiry_type": current.get("enquiry_type"),
        "notes": current.get("notes"),
        "booking_status": current.get(
            "booking_status", "not booked"
        ),
        "created_at": current.get(
            "created_at",
            datetime.now(timezone.utc).isoformat()
        ),
    }

    data.update(fields)

    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO customers (
                sender_id, platform, full_name, phone, email,
                service, enquiry_type, notes, booking_status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sender_id) DO UPDATE SET
                platform=excluded.platform,
                full_name=excluded.full_name,
                phone=excluded.phone,
                email=excluded.email,
                service=excluded.service,
                enquiry_type=excluded.enquiry_type,
                notes=excluded.notes,
                booking_status=excluded.booking_status
        """, (
            sender_id,
            data["platform"],
            data["full_name"],
            data["phone"],
            data["email"],
            data["service"],
            data["enquiry_type"],
            data["notes"],
            data["booking_status"],
            data["created_at"],
        ))


# Temporary conversation steps for testing
conversation_steps = {}


def detect_intent(message):
    text = message.lower().strip()

    if any(x in text for x in [
        "appointment", "book a call", "book a meeting",
        "schedule", "consultation", "calendar"
    ]):
        return "appointment"

    if any(x in text for x in [
        "price", "pricing", "cost", "charges",
        "how much", "quotation", "quote", "package"
    ]):
        return "pricing"

    if any(x in text for x in [
        "service", "services", "what do you offer",
        "what do you do"
    ]):
        return "services"

    if any(x in text for x in ["hi", "hello", "hey"]):
        return "greeting"

    return "general"


def get_service_match(message):
    text = message.lower()

    keywords = {
        "Website Development": ["website", "web development"],
        "Mobile App Development": ["mobile app", "android app", "ios app"],
        "Software Development": ["software", "custom software"],
        "Web 3.0 & Blockchain": ["blockchain", "web3", "web 3.0"],
        "Penetration Testing": ["penetration testing", "pentest"],
        "Web Security": ["web security", "cybersecurity", "security"],
        "Digital Marketing": ["digital marketing", "social media marketing"],
        "SEO": ["seo", "search engine optimization"],
        "Communication & Support": ["support", "communication"],
        "AI Services": ["ai services", "artificial intelligence", "ai agent"],
        "DevOps Services": ["devops", "cloud computing"],
    }

    for service, terms in keywords.items():
        if any(term in text for term in terms):
            return service

    return None


def get_reply(sender_id, platform, message):
    message = message.strip()

    if not message:
        return "Please send a message so I can help you."

    customer = get_customer(sender_id) or {}
    step = conversation_steps.get(sender_id)
    intent = detect_intent(message)

    # Continue collecting information already requested
    if step == "name":
        save_customer(sender_id, platform, full_name=message)
        conversation_steps[sender_id] = "phone"
        return "Thank you! Please share your contact number."

    if step == "phone":
        if len(message) < 7:
            return "Please enter a valid contact number."

        save_customer(sender_id, platform, phone=message)
        conversation_steps[sender_id] = "email"
        return (
            "Thank you! Please share your email address, "
            "or type Skip if you prefer not to share it."
        )

    if step == "email":
        email = None if message.lower() == "skip" else message

        save_customer(sender_id, platform, email=email)
        conversation_steps[sender_id] = "service"

        return "Which TechClues service are you interested in?"

    if step == "service":
        service = get_service_match(message) or message

        save_customer(sender_id, platform, service=service)
        conversation_steps[sender_id] = "notes"

        return (
            "Please briefly describe what you need, "
            "so our team can understand your requirements."
        )

    if step == "notes":
        save_customer(sender_id, platform, notes=message)
        conversation_steps.pop(sender_id, None)

        customer = get_customer(sender_id) or {}

        if customer.get("enquiry_type") == "pricing":
            return (
                "Thank you! Our team will contact you within "
                "30 minutes regarding your pricing enquiry."
            )

        if customer.get("enquiry_type") == "appointment":
            return (
                "Thank you! Please choose your preferred "
                "available slot using our booking calendar:\n"
                f"{BOOKING_LINK}\n\n"
                "Your appointment is confirmed only after "
                "the booking is completed."
            )

        return (
            "Thank you! We have recorded your enquiry. "
            "Our team can follow up with you."
        )

    # Greeting
    if intent == "greeting":
        return (
            "Hi! How can I help you today? "
            "How can I assist you?"
        )

    # Service catalogue
    if intent == "services":
        lines = "\n".join(
            f"- {name}: {url}"
            for name, url in SERVICES.items()
        )
        return (
            "Here are our TechClues services:\n\n"
            f"{lines}\n\n"
            f"Website: {WEBSITE}\n\n"
            "Which service are you interested in?"
        )

    # Identify a specific service
    service = get_service_match(message)

    if service:
        save_customer(sender_id, platform, service=service)
        return (
            f"We offer {service} services.\n"
            f"Learn more: {SERVICES[service]}\n\n"
            "Would you like to discuss your requirements "
            "or book a consultation?"
        )

    # Pricing: collect details before promising follow-up
    if intent == "pricing":
        save_customer(
            sender_id,
            platform,
            enquiry_type="pricing"
        )
        conversation_steps[sender_id] = "name"

        return (
            "Our team will contact you within 30 minutes "
            "regarding your pricing enquiry.\n\n"
            "First, may I have your full name?"
        )

    # Appointment: collect details and share calendar
    if intent == "appointment":
        save_customer(
            sender_id,
            platform,
            enquiry_type="appointment"
        )
        conversation_steps[sender_id] = "name"

        return (
            "Certainly! I can help you arrange a consultation.\n"
            "May I have your full name first?"
        )

    return (
        "Thank you for contacting TechClues!\n"
        "You can explore our services here: "
        f"{WEBSITE}\n\n"
        "You can ask me about our services, pricing, "
        "or appointment booking."
    )


@app.get("/")
def home():
    return {
        "status": "online",
        "message": "TechClues Social AI is running."
    }


@app.post("/reply")
def reply(data: IncomingMessage):
    return {
        "reply": get_reply(
            data.sender_id,
            data.platform,
            data.message
        )
    }