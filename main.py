
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client

app = FastAPI(title="TechClues Social AI")

Configure these in your hosting environment.

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
raise RuntimeError(
"Set SUPABASE_URL and SUPABASE_KEY environment variables."
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

WEBSITE = "https://techclues.co.uk/"
BOOKING_LINK = (
"https://api.leadconnectorhq.com/widget/booking/"
"3OD65zni7fQ51wVWzKny"
)

SERVICE_LINKS = {
"Website Development": "https://techclues.co.uk/website-development",
"Digital Marketing": "https://techclues.co.uk/digital-marketing",
"AI Services": "https://techclues.co.uk/ai-services",
}

conversation_steps = {}

class IncomingMessage(BaseModel):
sender_id: str
message: str
platform: str = "test"

def get_customer(sender_id):
result = (
supabase.table("customers")
.select("*")
.eq("sender_id", sender_id)
.limit(1)
.execute()
)
return result.data[0] if result.data else None

def save_customer(sender_id, platform, **fields):
current = get_customer(sender_id) or {}

row = {
    "sender_id": sender_id,
    "platform": platform,
    "name": current.get("name") or "Unknown Customer",
    "email": current.get("email"),
    "phone": current.get("phone"),
    "service": current.get("service"),
    "enquiry_type": current.get("enquiry_type"),
    "notes": current.get("notes"),
    "booking_status": (
        current.get("booking_status") or "not booked"
    ),
    "created_at": (
        current.get("created_at")
        or datetime.now(timezone.utc).isoformat()
    ),
}

if "full_name" in fields:
    fields["name"] = fields.pop("full_name")

row.update(fields)

supabase.table("customers").upsert(
    row, on_conflict="sender_id"
).execute()

return row

def get_services():
result = (
supabase.table("services")
.select("id,service_name,description,price,currency")
.execute()
)
return result.data or []

def detect_intent(message):
text = message.lower()

if any(x in text for x in [
    "appointment", "book a call", "book a meeting",
    "schedule", "consultation", "calendar", "booking"
]):
    return "appointment"

if any(x in text for x in [
    "price", "pricing", "cost", "charges",
    "how much", "quotation", "quote", "package"
]):
    return "pricing"

if any(x in text for x in [
    "services", "service", "what do you offer",
    "what do you do"
]):
    return "services"

if any(x in text for x in [
    "hi", "hello", "hey", "salam", "assalam"
]):
    return "greeting"

return "general"

def get_service_match(message):
text = message.lower()

keywords = {
    "Website Development": ["website", "web development"],
    "Mobile App Development": [
        "mobile app", "android app", "ios app"
    ],
    "Software Development": ["software", "custom software"],
    "Web 3.0 & Blockchain": ["blockchain", "web3", "web 3.0"],
    "Penetration Testing": ["penetration testing", "pentest"],
    "Web Security": ["web security", "cybersecurity"],
    "Digital Marketing": [
        "digital marketing", "social media marketing"
    ],
    "SEO": ["seo", "search engine optimization"],
    "Communication & Support": ["support", "communication"],
    "AI Services": [
        "ai services", "artificial intelligence", "ai agent"
    ],
    "DevOps Services": ["devops", "cloud computing"],
}

for service, terms in keywords.items():
    if any(term in text for term in terms):
        return service

for service in get_services():
    name = service.get("service_name", "")
    if name and name.lower() in text:
        return name

return None

def get_reply(sender_id, platform, message):
message = message.strip()

if not message:
    return "Please send a message so I can help you."

customer = get_customer(sender_id) or {}
step = conversation_steps.get(sender_id)
intent = detect_intent(message)

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

    if email and ("@" not in email or "." not in email):
        return "Please enter a valid email address or type Skip."

    save_customer(sender_id, platform, email=email)
    conversation_steps[sender_id] = "service"
    return "Which TechClues service are you interested in?"

if step == "service":
    service = get_service_match(message) or message
    save_customer(sender_id, platform, service=service)
    conversation_steps[sender_id] = "notes"
    return "Please briefly describe your requirements."

if step == "notes":
    save_customer(sender_id, platform, notes=message)
    conversation_steps.pop(sender_id, None)

    customer = get_customer(sender_id) or {}

    if customer.get("enquiry_type") == "appointment":
        return (
            "Thank you! Please choose an available slot "
            "using our booking calendar:\n"
            f"{BOOKING_LINK}\n\n"
            "Your appointment is confirmed only after "
            "you complete the booking."
        )

    return (
        "Thank you! Your enquiry has been recorded. "
        "Our team can follow up with you."
    )

if intent == "greeting":
    return "Hi! Welcome to TechClues. How can I help you today?"

if intent == "services":
    services = get_services()

    if not services:
        return "Our services list is currently unavailable."

    lines = []
    for item in services:
        name = item["service_name"]
        description = item.get("description") or ""
        price = item.get("price")
        currency = item.get("currency") or ""

        if price is None or float(price) == 0:
            price_text = "Contact us for a quotation"
        else:
            price_text = f"{currency} {price}".strip()

        lines.append(
            f"- {name}: {description}\n  Price: {price_text}"
        )

    return (
        "Here are our services:\n\n"
        + "\n".join(lines)
        + f"\n\nWebsite: {WEBSITE}"
    )

if intent in ("pricing", "appointment"):
    save_customer(
        sender_id,
        platform,
        enquiry_type=intent
    )
    conversation_steps[sender_id] = "name"

    if intent == "pricing":
        return (
            "Our pricing depends on your requirements. "
            "May I have your full name so we can record your enquiry?"
        )

    return (
        "Certainly! May I have your full name to start "
        "your consultation request?"
    )

service = get_service_match(message)

if service:
    save_customer(sender_id, platform, service=service)
    link = SERVICE_LINKS.get(service, WEBSITE)

    return (
        f"We offer {service} services.\n"
        f"Learn more: {link}\n\n"
        "Would you like to discuss your requirements "
        "or book a consultation?"
    )

return (
    "Thank you for contacting TechClues!\n"
    f"Explore our services: {WEBSITE}\n"
    "Ask me about services, pricing, or appointments."
)

@app.get("/")
def home():
return {
"status": "online",
"message": "TechClues Social AI is running."
}

@app.get("/services")
def services_endpoint():
try:
return {"services": get_services()}
except Exception as exc:
raise HTTPException(
status_code=500,
detail="Could not retrieve services from Supabase."
) from exc

@app.post("/reply")
def reply(data: IncomingMessage):
try:
return {
"reply": get_reply(
data.sender_id,
data.platform,
data.message
)
}
except Exception as exc:
print(f"Reply error: {exc}")
raise HTTPException(
status_code=500,
detail="Could not process the message. Check server logs."
) from exc
