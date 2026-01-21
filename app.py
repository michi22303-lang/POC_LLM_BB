import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import os
import time
import random
from datetime import datetime

# --- 0. PAGE CONFIG ---
st.set_page_config(page_title="SBH Pilot", page_icon="🤖", layout="wide")

# --- 1. CONFIG & DATA ---
MOCK_MODE = True 

USERS = {
    "michael.soth": {"name": "Michael Soth", "password": "Start123!", "email": "michael.soth@sbh.hamburg.de"},
    "tester":       {"name": "Test User",    "password": "Start123!", "email": "team@sbh.hamburg.de"}
}

MODELS = {
    "gemini-1.5-flash": {"input": 0.10, "output": 0.40, "name": "Google Gemini Flash ⚡"},
    "gemini-1.5-pro":   {"input": 1.25, "output": 5.00, "name": "Google Gemini Pro 🧠"},
    "gpt-4o":           {"input": 2.50, "output": 10.00, "name": "OpenAI GPT-4o 🚀"},
    "mistral-large":    {"input": 2.00, "output": 6.00, "name": "Mistral Large 🇪🇺"}
}

# --- 2. AUTHENTICATION ---
names = [u["name"] for u in USERS.values()]
usernames = list(USERS.keys())
passwords = [u["password"] for u in USERS.values()]
hashed_passwords = stauth.Hasher(passwords).generate()

credentials = {"usernames": {}}
for i, username in enumerate(usernames):
    credentials["usernames"][username] = {
        "name": names[i],
        "password": hashed_passwords[i],
        "email": USERS[username]["email"]
    }

authenticator = stauth.Authenticate(credentials, "sbh_cookie_v2", "key_v2_123", 30)

# --- 3. HELPER FUNCTIONS ---
def save_log(file, data):
    df = pd.DataFrame([data])
    if not os.path.exists(file):
        df.to_csv(file, index=False)
    else:
        df.to_csv(file, mode='a', header=False, index=False)

def get_response_mock(model_key, prompt):
    time.sleep(1.0) 
    model_name = MODELS[model_key]['name']
    
    # Prefix einbauen (z.B. "Mistral Large: ...")
    prefix = f"**{model_name}**: "
    
    in_tok = len(prompt) * 2
    out_tok = random.randint(100, 400)
    
    raw_responses = [
        "Das ist eine relevante Frage für die SBH. Basierend auf den Daten würde ich sagen: Wir sollten Prozess A priorisieren.",
        "Hier ist der Python-Code, den du wolltest. Er ist effizient und sicher.",
        "Zusammenfassend lässt sich sagen: Die Kosten sind im Rahmen, aber die Qualität muss überwacht werden."
    ]
    # Antwort zusammensetzen: Name + Text
    full_response = prefix + random.choice(raw_responses)
    
    return full_response, in_tok, out_tok

def calc_cost(model, in_tok, out_tok):
    return (in_tok/1e6 * MODELS[model]["input"]) + (out_tok/1e6 * MODELS[model]["output"])

# --- 4. MAIN APP ---
authenticator.login()

if st.session_state["authentication_status"]:
    user_id = st.session_state["username"]
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("SBH Pilot")
        st.write(f"User: **{USERS[user_id]['name']}**")
        
        page = "Chat"
        if user_id == "michael.soth":
            st.divider()
            page = st.radio("Navigation", ["💬 Chat & Eingabe", "📊 Admin Dashboard"])
        
        st.divider()
        authenticator.logout('Abmelden', 'sidebar')

    # --- VIEW 1: CHAT MIT EINGABE OBEN ---
    if page == "💬 Chat & Eingabe":
        
        st.subheader("KI-Abfrage")

        # 1. BEREICH: AUSWAHL & EINGABE (Ganz oben fixiert)
        with st.container():
            # Modellwahl
            selected_model = st.selectbox(
                "1. Modell auswählen:", 
                list(MODELS.keys()), 
                format_func=lambda x: MODELS[x]["name"]
            )
            
            # Eingabe Formular
            with st.form("chat_form", clear_on_submit=True):
                user_input = st.text_area("2. Deine Frage:", height=100, placeholder="Gib hier deine Frage ein...")
                submitted = st.form_submit_button("🚀 Absenden")
                
                if submitted and user_input:
                    # Logik ausführen
                    if "messages" not in st.session_state: st.session_state.messages = []
                    
                    # User Nachricht speichern
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    
                    # KI Antwort generieren
                    resp, in_t, out_t = get_response_mock(selected_model, user_input)
                    cost = calc_cost(selected_model, in_t, out_t)
                    
                    # Speichern
                    stats = f"Kosten: ${cost:.5f}"
                    st.session_state.messages.append({"role": "assistant", "content": resp, "stats": stats})
                    
                    save_log("usage.csv", {"time": datetime.now().strftime("%H:%M:%S"), "user": user_id, "model": selected_model, "cost": cost})
                    
                    # Seite neu laden, damit die neue Nachricht unten erscheint
                    st.rerun()

        st.divider()
        
        # 2. BEREICH: CHATVERLAUF (Erscheint darunter)
        st.subheader("📝 Verlauf (Aktuelle Sitzung)")
        
        if "messages" not in st.session_state: st.session_state.messages = []
        
        if not st.session_state.messages:
            st.info("Noch keine Nachrichten. Starte oben eine Anfrage!")
        
        # Verlauf rendern (von oben nach unten)
        for i, msg in enumerate(st.session_state.messages):
            avatar = "👤" if msg["role"] == "user" else "🤖"
            
            # Wir nutzen hier container für bessere Trennung
            with st.container():
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])
                    if "stats" in msg:
                        st.caption(msg["stats"])
            
            # Feedback Button nur unter der ALLERLETZTEN Nachricht, wenn sie vom Bot ist
            if i == len(st.session_state.messages) - 1 and msg["role"] == "assistant":
                st.write("---")
                # Feedback direkt hier
                fb = st.feedback("stars", key=f"feed_{len(st.session_state.messages)}")
                if fb is not None:
                    rating = fb + 1
                    save_log("feedback.csv", {"time": datetime.now().strftime("%H:%M:%S"), "user": user_id, "model": selected_model, "rating": rating})
                    st.toast(f"Bewertung ({rating} Sterne) gespeichert!", icon="✅")

    # --- VIEW 2: ADMIN DASHBOARD ---
    elif page == "📊 Admin Dashboard":
        st.title("Admin Cockpit")
        
        if os.path.exists("usage.csv"):
            df = pd.read_csv("usage.csv")
            c1, c2 = st.columns(2)
            c1.metric("Gesamtkosten", f"${df['cost'].sum():.4f}")
            c2.metric("Anzahl Prompts", len(df))
            
            st.subheader("Nutzung pro Modell")
            st.bar_chart(df.groupby("model")["cost"].sum())
            
            st.subheader("Letzte Logs")
            st.dataframe(df.tail(10))
        else:
            st.info("Keine Daten.")

elif st.session_state["authentication_status"] is False:
    st.error('Falsches Passwort')
elif st.session_state["authentication_status"] is None:
    st.warning('Bitte einloggen')
