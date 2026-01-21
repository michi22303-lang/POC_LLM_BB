import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import os
import time
import random
from datetime import datetime

# --- 1. KONFIGURATION (MOCK MODE AN) ---
MOCK_MODE = True 

# Deine User & Passwörter (Klartext hier okay, da Repo Private ist & wir live hashen)
USERS = {
    "michael.soth": {"name": "Michael Soth", "password": "Start123!", "email": "michael.soth@sbh.hamburg.de"},
    "tester":       {"name": "Test User",    "password": "Start123!", "email": "team@sbh.hamburg.de"}
}

MODELS = {
    "gemini-1.5-flash": {"input": 0.10, "output": 0.40, "provider": "google", "name": "Google Gemini Flash"},
    "gpt-4o":           {"input": 2.50, "output": 10.00, "provider": "openai", "name": "OpenAI GPT-4o"},
}

# --- 2. AUTHENTIFIZIERUNG (AUTO-HASHING) ---
# Wir generieren die Hashes live auf dem Server, damit du lokal nichts tun musst.
names = [u["name"] for u in USERS.values()]
usernames = list(USERS.keys())
passwords = [u["password"] for u in USERS.values()]

# Passwörter hashen
hashed_passwords = stauth.Hasher(passwords).generate()

# Config Struktur bauen
credentials = {"usernames": {}}
for i, username in enumerate(usernames):
    credentials["usernames"][username] = {
        "name": names[i],
        "password": hashed_passwords[i],
        "email": USERS[username]["email"]
    }

authenticator = stauth.Authenticate(
    credentials,
    "sbh_cookie_name",
    "random_signature_key_123",
    30
)

# --- 3. HELFER FUNKTIONEN ---
def log_usage(username, model, in_tok, out_tok, cost, prompt, response):
    file_path = "usage_log.csv"
    new_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": username, "model": model, "cost": cost,
        "prompt": prompt[:50], "response": response[:50]
    }
    df = pd.DataFrame([new_data])
    if not os.path.exists(file_path):
        df.to_csv(file_path, index=False)
    else:
        df.to_csv(file_path, mode='a', header=False, index=False)

def get_response(model_key, prompt):
    if MOCK_MODE:
        time.sleep(1)
        return f"**[MOCK]** Simuliere {MODELS[model_key]['name']}: '{prompt}'", len(prompt), 100
    return "Kein API Key", 0, 0

# --- 4. APP UI ---
authenticator.login()

if st.session_state["authentication_status"]:
    user = st.session_state["username"]
    
    with st.sidebar:
        st.write(f"User: **{st.session_state['name']}**")
        authenticator.logout('Logout', 'main')
        st.divider()
        model = st.selectbox("Modell", list(MODELS.keys()))
        if st.button("Reset"): st.session_state.messages = []; st.rerun()

    st.title("🤖 SBH Pilot")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])
        
    if prompt := st.chat_input("Nachricht..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        resp, in_tok, out_tok = get_response(model, prompt)
        cost = (in_tok/1e6 * MODELS[model]["input"]) + (out_tok/1e6 * MODELS[model]["output"])
        
        st.session_state.messages.append({"role": "assistant", "content": resp})
        st.chat_message("assistant").write(resp)
        st.caption(f"Kosten: ${cost:.5f}")
        
        log_usage(user, model, in_tok, out_tok, cost, prompt, resp)

    # ADMIN BEREICH
    if user == "michael.soth":
        st.divider()
        if st.checkbox("🔐 Admin Logs"):
            if os.path.exists("usage_log.csv"):
                st.dataframe(pd.read_csv("usage_log.csv"))
            else:
                st.info("Keine Daten.")

elif st.session_state["authentication_status"] is False:
    st.error('Passwort falsch')
elif st.session_state["authentication_status"] is None:
    st.warning('Bitte einloggen')
