import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import os
import time
import random
from datetime import datetime

# --- 0. SEITEN KONFIGURATION (MUSS GANZ OBEN STEHEN) ---
st.set_page_config(page_title="SBH Pilot", page_icon="🤖", layout="wide")

# --- 1. KONFIGURATION & DATEN ---
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

# --- 2. AUTH SETUP ---
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

authenticator = stauth.Authenticate(credentials, "sbh_cookie_modern", "key_modern_123", 30)

# --- 3. HELFER FUNKTIONEN ---
def save_log(file, data):
    df = pd.DataFrame([data])
    if not os.path.exists(file):
        df.to_csv(file, index=False)
    else:
        df.to_csv(file, mode='a', header=False, index=False)

def get_response_mock(model_key, prompt):
    time.sleep(1.2) 
    model_name = MODELS[model_key]['name']
    
    # Simuliere unterschiedliche Längen für Realismus
    in_tok = len(prompt) * 2
    out_tok = random.randint(150, 600)
    
    responses = [
        f"Hier ist eine detaillierte Antwort basierend auf dem Modell **{model_name}**.\n\n* Punkt 1: Analyse der Anfrage '{prompt}'\n* Punkt 2: Datenverarbeitung\n* Punkt 3: Ergebnisgenerierung",
        f"Moin! Als **{model_name}** habe ich folgende Lösung für dich:\n```python\nprint('Hallo SBH')\n```\nFunktioniert das für dich?",
        f"Das ist eine komplexe Frage. Mit der Rechenkraft von **{model_name}** komme ich zu dem Schluss, dass wir Option B wählen sollten."
    ]
    return random.choice(responses), in_tok, out_tok

def calc_cost(model, in_tok, out_tok):
    return (in_tok/1e6 * MODELS[model]["input"]) + (out_tok/1e6 * MODELS[model]["output"])

# --- 4. APP START ---
authenticator.login()

if st.session_state["authentication_status"]:
    user_id = st.session_state["username"]
    
    # --- SIDEBAR DESIGN ---
    with st.sidebar:
        st.title("🤖 SBH Pilot")
        st.write(f"Angemeldet: **{USERS[user_id]['name']}**")
        
        # Navigation für Admin
        page = "Chat"
        if user_id == "michael.soth":
            st.divider()
            page = st.radio("Menü", ["💬 Chat", "📊 Admin Dashboard"], index=0)
        
        st.divider()
        authenticator.logout('Abmelden', 'sidebar')

    # --- VIEW 1: CHAT ---
    if page == "💬 Chat":
        
        # Header Area
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("KI-Assistenzsystem")
        with col2:
            # Modell Auswahl kompakt oben rechts
            selected_model = st.selectbox("", list(MODELS.keys()), format_func=lambda x: MODELS[x]["name"], label_visibility="collapsed")

        if "messages" not in st.session_state: st.session_state.messages = []

        # Chat History
        for msg in st.session_state.messages:
            avatar = "👤" if msg["role"] == "user" else "🤖"
            with st.chat_message(msg["role"], avatar=avatar):
                st.write(msg["content"])
                # Wenn Stats vorhanden sind (in metadata gespeichert), anzeigen
                if "stats" in msg:
                    st.caption(f"💰 {msg['stats']}")

        # Input
        if prompt := st.chat_input("Deine Frage stellen..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user", avatar="👤").write(prompt)

            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Generiere Antwort..."):
                    resp, in_t, out_t = get_response_mock(selected_model, prompt)
                    cost = calc_cost(selected_model, in_t, out_t)
                    
                    st.markdown(resp)
                    
                    # Modernes Info-Badge
                    stats_txt = f"Kosten: ${cost:.5f} ({in_t} In / {out_t} Out)"
                    st.caption(stats_txt)
                    
                    # Speichern im State
                    st.session_state.messages.append({"role": "assistant", "content": resp, "stats": stats_txt})
                    
                    save_log("usage.csv", {
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "user": user_id, "model": selected_model, "cost": cost
                    })
            
            # Damit das Feedback-Element neu geladen wird
            st.rerun()

        # FEEDBACK BEREICH (Erscheint nur nach der letzten KI Antwort)
        if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "assistant":
            st.divider()
            st.write("Wie war diese Antwort?")
            
            # MODERNE STERNE BEWERTUNG
            feedback = st.feedback("stars", key=f"fb_{len(st.session_state.messages)}")
            
            if feedback is not None:
                # Feedback speichern
                rating = feedback + 1 # Streamlit gibt 0-4 zurück, wir wollen 1-5
                save_log("feedback.csv", {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "user": user_id, "model": selected_model, "rating": rating
                })
                st.toast(f"Danke für {rating} Sterne! ⭐", icon="✅")

    # --- VIEW 2: ADMIN DASHBOARD ---
    elif page == "📊 Admin Dashboard":
        st.title("Admin Cockpit")
        st.markdown("Überblick über Kosten und Qualität.")
        
        if os.path.exists("usage.csv"):
            df_usage = pd.read_csv("usage.csv")
            total = df_usage["cost"].sum()
            count = len(df_usage)
            
            # Moderne KPI Karten
            c1, c2, c3 = st.columns(3)
            c1.metric("Gesamtkosten", f"${total:.4f}")
            c2.metric("Anfragen gesamt", count)
            c3.metric("Nutzer aktiv", df_usage["user"].nunique())
            
            st.divider()
            
            c_chart1, c_chart2 = st.columns(2)
            
            with c_chart1:
                st.subheader("Kosten pro Modell")
                cost_chart = df_usage.groupby("model")["cost"].sum()
                st.bar_chart(cost_chart, color="#FF4B4B") # Streamlit Rot
            
            with c_chart2:
                if os.path.exists("feedback.csv"):
                    st.subheader("Qualität (Sterne)")
                    df_feed = pd.read_csv("feedback.csv")
                    # Durchschnitt berechnen
                    avg = df_feed.groupby("model")["rating"].mean()
                    st.bar_chart(avg, color="#00CC96") # Grün
                else:
                    st.info("Noch kein Feedback.")

            with st.expander("Detaillierte Rohdaten ansehen"):
                st.dataframe(df_usage.sort_values("time", ascending=False), use_container_width=True)

        else:
            st.info("Noch keine Daten vorhanden. Starte den ersten Chat!")

elif st.session_state["authentication_status"] is False:
    st.error('Passwort falsch')
elif st.session_state["authentication_status"] is None:
    st.warning('Bitte anmelden.')
