import streamlit as st
from supabase import create_client, Client
from datetime import date

st.set_page_config(
    page_title="AI Social Assistant",
    page_icon="🤖"
)

# Supabase connection
@st.cache_resource
def connect_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

try:
    supabase = connect_supabase()
    connected = True
except Exception:
    supabase = None
    connected = False

# Add your actual website services and prices here
SERVICES = {
    "web development": "Website development",
    "web design": "Website design",
    "digital marketing": "Digital marketing",
    "seo": "Search engine optimization",
    "software development": "Software development",
}

st.title("🤖 AI Social Assistant")
st.write("Welcome! Ask me about our services, pricing, or appointments.")

if not connected:
    st.warning(
        "Database connection failed. "
        "Please check your Supabase credentials in Streamlit Secrets."
    )

# Simple chatbot
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hello! 👋 How can I help you today? "
                "You can ask about services, pricing, or appointments."
            ),
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

user_message = st.chat_input("Type your message...")

if user_message:
    st.session_state.messages.append(
        {"role": "user", "content": user_message}
    )

    query = user_message.lower()

    if any(word in query for word in ["hello", "hi", "hey", "salam"]):
        answer = "Hello! 👋 How can I help you with our services today?"

    elif any(word in query for word in ["appointment", "booking", "book", "schedule"]):
        answer = (
            "You can request an appointment using the form below. "
            "Please provide your details and preferred date."
        )

    elif any(word in query for word in ["price", "pricing", "cost", "rate", "charges"]):
        answer = (
            "Our pricing depends on the service and project requirements. "
            "Please tell me which service you need, and our team can confirm "
            "the exact price. No prices have been configured yet."
        )

    elif any(word in query for word in ["service", "services", "offer", "provide"]):
        answer = "Our listed service categories are:\n" + "\n".join(
            f"- {name.title()}" for name in SERVICES
        ) + "\nPlease confirm the available services with our team."

    else:
        answer = (
            "Thanks for your message! Please ask about services, pricing, "
            "or appointments. For other questions, our team can assist you."
        )

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
    st.rerun()

st.divider()
st.subheader("📅 Request an Appointment")

with st.form("appointment_form"):
    name = st.text_input("Full name")
    email = st.text_input("Email (optional)")
    phone = st.text_input("Phone number")
    service = st.selectbox(
        "Select service",
        ["Website development", "Website design",
         "Digital marketing", "SEO", "Software development", "Other"]
    )
    appointment_date = st.date_input(
        "Preferred appointment date",
        value=date.today(),
        min_value=date.today()
    )
    submitted = st.form_submit_button("Submit Appointment Request")

if submitted:
    if not name.strip() or not phone.strip():
        st.error("Please enter your name and phone number.")
    elif not connected:
        st.error("Database is not connected. Please try again later.")
    else:
        try:
            result = supabase.table("customers").insert({
                "name": name.strip(),
                "email": email.strip() or None,
                "phone": phone.strip(),
                "service": service,
                "appointment_date": appointment_date.isoformat()
            }).execute()

            st.success(
                "Your appointment request has been submitted! "
                "The team will confirm availability."
            )
        except Exception as error:
            st.error(
                "Could not save your request. Check the database table "
                "and its permissions in Supabase."
            )
