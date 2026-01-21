import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import os
import time
import random
from datetime import datetime

# --- 0. PAGE CONFIG ---
st.set_page_config(page_title="LLM Pilot Bildungsbau", page_icon="🤖", layout="wide")

# --- 1. CONFIG & MOCK DATA ---
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

authenticator = stauth.Authenticate(credentials, "sbh_cookie_v4", "key_v4_fixed", 30)

# --- 3. HELPER FUNCTIONS ---
def save_log(file, data):
    df = pd.DataFrame([data])
    if not os.path.exists(file):
        df.to_csv(file, index=False)
    else:
        df.to_csv(file, mode='a', header=False, index=False)

def get_response_mock(model_key, prompt, filename=None):
    time.sleep(1.0) # Denken simulieren
    model_name = MODELS[model_key]['name']
    
    # Prefix
    prefix = f"**{model_name}**: "
    
    # Datei-Erkennung simulieren
    file_msg = ""
    if filename:
        file_msg = f"\n*(Ich beziehe mich auf die Datei '{filename}')* "
        
    responses = [
        f"Das ist ein wichtiger Punkt.{file_msg} Hier ist meine Analyse dazu...",
        f"Moin!{file_msg} Basierend auf deiner Eingabe habe ich folgenden Vorschlag erarbeitet.",
        f"Hier sind die Daten, die du angefordert hast.{file_msg} Bitte prüfe Punkt 3 besonders genau."
    ]
    
    full_response = prefix + random.choice(responses)
    in_tok = len(prompt) * 2 + (500 if filename else 0)
    out_tok = random.randint(150, 500)
    
    return full_response, in_tok, out_tok

def calc_cost(model, in_tok, out_tok):
    return (in_tok/1e6 * MODELS[model]["input"]) + (out_tok/1e6 * MODELS[model]["output"])

# --- 4. FEEDBACK DIALOG ---
@st.dialog("⭐ Bewertung abgeben")
def feedback_modal(user, model):
    st.write("Wie zufrieden bist du mit der letzten Antwort?")
    
    # Streamlit Feedback Stars
    rating = st.feedback("stars")
    comment = st.text_input("Kommentar (optional)")
    
    if st.button("Absenden"):
        if rating is not None:
            final_rating = rating + 1
            save_log("feedback.csv", {
                "time": datetime.now().strftime("%H:%M:%S"), 
                "user": user, 
                "model": model, 
                "rating": final_rating, 
                "comment": comment
            })
            st.success("Danke!")
            time.sleep(0.5)
            st.session_state.show_feedback = False # Reset
            st.rerun()
        else:
            st.warning("Bitte Sterne wählen.")

# --- 5. MAIN APP ---
authenticator.login()

if st.session_state["authentication_status"]:
    user_id = st.session_state["username"]
    
    # State Init
    if "messages" not in st.session_state: st.session_state.messages = []
    if "show_feedback" not in st.session_state: st.session_state.show_feedback = False
    if "last_model" not in st.session_state: st.session_state.last_model = list(MODELS.keys())[0]

    # --- SIDEBAR (ALLES WAS NICHT CHAT IST) ---
    with st.sidebar:
        st.header("⚙️ Steuerung")
        st.write(f"Angemeldet: **{USERS[user_id]['name']}**")
        
        # Admin Weiche
        page = "Chat"
        if user_id == "michael.soth":
            st.divider()
            page = st.radio("Navigation", ["💬 Chat", "📊 Admin Dashboard"])
        
        if page == "💬 Chat":
            st.divider()
            st.subheader("Modell & Daten")
            
            # 1. MODELL WAHL
            selected_model = st.selectbox(
                "KI-Modell:", 
                list(MODELS.keys()), 
                format_func=lambda x: MODELS[x]["name"]
            )
            
            # 2. FILE UPLOAD
            uploaded_file = st.file_uploader("Dokument anhängen:", type=["pdf", "docx", "txt", "csv"])
            if uploaded_file:
                st.success(f"📎 {uploaded_file.name} bereit")

            # 3. CLEAR CHAT
            st.divider()
            if st.button("🗑️ Chat leeren", type="primary"):
                st.session_state.messages = []
                st.session_state.show_feedback = False
                st.rerun()

        st.divider()
        authenticator.logout('Abmelden', 'sidebar')

    # --- VIEW 1: CHAT ---
    if page == "💬 Chat":
        st.title("🤖 SBH KI-Pilot")
        
        # Chat History rendern
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
                st.markdown(msg["content"])
                if "stats" in msg:
                    st.caption(msg["stats"])

        # INPUT FELD (UNTEN, WIE GEWOHNT)
        if prompt := st.chat_input("Deine Nachricht an die KI..."):
            
            # Datei Info dazu mogeln, falls vorhanden
            file_name = uploaded_file.name if uploaded_file else None
            full_prompt = prompt
            if file_name:
                full_prompt = f"{prompt} [Anhang: {file_name}]"

            # 1. User Message anzeigen & speichern
            st.session_state.messages.append({"role": "user", "content": full_prompt})
            with st.chat_message("user", avatar="👤"):
                st.write(full_prompt)

            # 2. KI Antwort generieren
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Generiere..."):
                    resp, in_t, out_t = get_response_mock(selected_model, prompt, file_name)
                    cost = calc_cost(selected_model, in_t, out_t)
                    
                    st.markdown(resp)
                    stats = f"Kosten: ${cost:.5f}"
                    st.caption(stats)
                    
                    st.session_state.messages.append({"role": "assistant", "content": resp, "stats": stats})
                    
                    # Loggen
                    save_log("usage.csv", {"time": datetime.now().strftime("%H:%M:%S"), "user": user_id, "model": selected_model, "cost": cost})
                    
                    # Trigger für Feedback setzen
                    st.session_state.show_feedback = True
                    st.session_state.last_model = selected_model
                    st.rerun() # Neuladen, um Dialog zu öffnen

        # DIALOG CHECK (Muss nach Rerun passieren)
        if st.session_state.show_feedback:
            feedback_modal(user_id, st.session_state.last_model)

    # --- VIEW 2: ADMIN DASHBOARD ---
    elif page == "📊 Admin Dashboard":
        st.title("Admin Cockpit")
        
        if os.path.exists("usage.csv"):
            df = pd.read_csv("usage.csv")
            
            # Metriken
            col1, col2, col3 = st.columns(3)
            col1.metric("Gesamtkosten", f"${df['cost'].sum():.4f}")
            col2.metric("Interaktionen", len(df))
            col3.metric("User", df['user'].nunique())
            
            st.divider()
            
            # Grafiken
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Kosten pro Modell")
                st.bar_chart(df.groupby("model")["cost"].sum())
            with c2:
                if os.path.exists("feedback.csv"):
                    st.subheader("Bewertung (Ø Sterne)")
                    df_fb = pd.read_csv("feedback.csv")
                    st.bar_chart(df_fb.groupby("model")["rating"].mean(), color="#00ff00")
                else:
                    st.info("Noch kein Feedback.")

            st.subheader("Letzte Logs")
            st.dataframe(df.sort_values("time", ascending=False).head(10), use_container_width=True)
            
        else:
            st.info("Noch keine Daten verfügbar.")

elif st.session_state["authentication_status"] is False:
    st.error('Falsches Passwort')
elif st.session_state["authentication_status"] is None:
    st.warning('Bitte anmelden.')
