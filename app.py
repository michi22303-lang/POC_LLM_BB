import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import os
import time
import random
from datetime import datetime

# --- 1. KONFIGURATION & DATEN ---
MOCK_MODE = True 

# User Datenbank (Klartext für Demo ok, da Repo private)
USERS = {
    "michael.soth": {"name": "Michael Soth", "password": "Start123!", "email": "michael.soth@sbh.hamburg.de"},
    "tester":       {"name": "Test User",    "password": "Start123!", "email": "team@sbh.hamburg.de"}
}

# Jetzt 4 Modelle zur Auswahl
MODELS = {
    "gemini-1.5-flash": {"input": 0.10, "output": 0.40, "name": "Google Gemini Flash (Schnell)"},
    "gemini-1.5-pro":   {"input": 1.25, "output": 5.00, "name": "Google Gemini Pro (Smart)"},
    "gpt-4o":           {"input": 2.50, "output": 10.00, "name": "OpenAI GPT-4o (High-End)"},
    "mistral-large":    {"input": 2.00, "output": 6.00, "name": "Mistral Large (EU-Datenschutz)"}
}

# --- 2. AUTH SETUP (Live-Hashing) ---
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

authenticator = stauth.Authenticate(credentials, "sbh_cookie", "key123", 30)

# --- 3. LOGIC & FILES ---
def save_log(file, data):
    df = pd.DataFrame([data])
    if not os.path.exists(file):
        df.to_csv(file, index=False)
    else:
        df.to_csv(file, mode='a', header=False, index=False)

def get_response_mock(model_key, prompt):
    time.sleep(1.2) # Denken simulieren
    model_name = MODELS[model_key]['name']
    
    # Simuliere unterschiedliche Längen/Kosten
    in_tok = len(prompt) // 2
    out_tok = random.randint(100, 500)
    
    responses = [
        f"Das ist ein interessanter Punkt zu '{prompt}'. Aus Sicht von **{model_name}** würde ich sagen: Wir müssen die Prozesse optimieren.",
        f"Hier ist der Entwurf, den du wolltest. Generiert mit **{model_name}**.",
        f"Zu deiner Frage '{prompt}': Die Datenlage ist eindeutig. (Simulierte Antwort)."
    ]
    return random.choice(responses), in_tok, out_tok

def calc_cost(model, in_tok, out_tok):
    return (in_tok/1e6 * MODELS[model]["input"]) + (out_tok/1e6 * MODELS[model]["output"])

# --- 4. APP START ---
authenticator.login()

if st.session_state["authentication_status"]:
    user_id = st.session_state["username"]
    
    # --- NAVIGATION (ADMIN WEICHE) ---
    st.sidebar.title(f"Moin, {USERS[user_id]['name'].split()[0]}!")
    
    page = "Chat" # Standard für alle
    
    # Admin Menü nur für Michael
    if user_id == "michael.soth":
        st.sidebar.divider()
        st.sidebar.subheader("👨‍✈️ Admin Bereich")
        page = st.sidebar.radio("Navigation:", ["💬 Chat nutzen", "📊 Dashboard & Kosten"])
    
    st.sidebar.divider()
    authenticator.logout('Logout', 'sidebar')

    # --- SEITE 1: CHAT ---
    if page == "💬 Chat nutzen" or page == "Chat":
        
        # Einstellungen
        with st.sidebar:
            st.subheader("Einstellungen")
            selected_model = st.selectbox("Modell wählen:", list(MODELS.keys()), format_func=lambda x: MODELS[x]["name"])
            if st.button("🗑️ Chat leeren"):
                st.session_state.messages = []
                st.rerun()

        st.title("🤖 SBH KI-Pilot")
        st.caption("Testumgebung für LLM-Evaluierung")

        if "messages" not in st.session_state: st.session_state.messages = []

        # Verlauf anzeigen
        for msg in st.session_state.messages:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
            st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

        # Input
        if prompt := st.chat_input("Deine Nachricht..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user", avatar="🧑‍💻").write(prompt)

            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner(f"{MODELS[selected_model]['name']} generiert..."):
                    resp, in_t, out_t = get_response_mock(selected_model, prompt)
                    cost = calc_cost(selected_model, in_t, out_t)
                    
                    st.markdown(resp)
                    st.caption(f"💰 Kosten: ${cost:.5f} | In: {in_t} | Out: {out_t}")
                    
                    st.session_state.messages.append({"role": "assistant", "content": resp})
                    
                    # Loggen
                    save_log("usage.csv", {
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "user": user_id, "model": selected_model, "cost": cost
                    })

        # FEEDBACK FORMULAR (Immer unter dem Chat wenn Nachrichten da sind)
        if len(st.session_state.messages) > 1:
            st.divider()
            st.info("📝 Bitte bewerte die letzte Antwort für unsere Auswertung:")
            with st.form("feedback_form"):
                c1, c2 = st.columns([1, 3])
                rating = c1.slider("Sterne", 1, 5, 3)
                comment = c2.text_input("Kommentar (Was war gut/schlecht?)")
                
                if st.form_submit_button("Bewertung senden"):
                    save_log("feedback.csv", {
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "user": user_id, "model": selected_model, "rating": rating, "comment": comment
                    })
                    st.success("Danke! Feedback gespeichert.")
                    time.sleep(1)
                    st.rerun()

    # --- SEITE 2: ADMIN DASHBOARD ---
    elif page == "📊 Dashboard & Kosten":
        st.title("📊 Admin Auswertung")
        
        tab1, tab2 = st.tabs(["💰 Kosten-Analyse", "⭐ Qualitäts-Feedback"])
        
        with tab1:
            if os.path.exists("usage.csv"):
                df_usage = pd.read_csv("usage.csv")
                
                # KPIs
                total = df_usage["cost"].sum()
                st.metric("Gesamtkosten (Simuliert)", f"${total:.4f}", delta="Mock-Mode aktiv")
                
                st.subheader("Kosten pro Modell")
                # Chart: Welches Modell kostet uns am meisten?
                cost_by_model = df_usage.groupby("model")["cost"].sum()
                st.bar_chart(cost_by_model)
                
                st.subheader("Rohdaten")
                st.dataframe(df_usage)
            else:
                st.info("Noch keine Chat-Daten vorhanden.")
                
        with tab2:
            if os.path.exists("feedback.csv"):
                df_feed = pd.read_csv("feedback.csv")
                
                st.subheader("Durchschnittsbewertung je Modell")
                avg_rating = df_feed.groupby("model")["rating"].mean()
                st.bar_chart(avg_rating)
                
                st.subheader("User Kommentare")
                for index, row in df_feed.iterrows():
                    st.text(f"⭐⭐⭐ ({row['rating']}/5) - {row['model']}: {row['comment']}")
                    st.divider()
            else:
                st.warning("Noch kein Feedback abgegeben.")

elif st.session_state["authentication_status"] is False:
    st.error('Passwort falsch')
elif st.session_state["authentication_status"] is None:
    st.warning('Bitte anmelden.')
