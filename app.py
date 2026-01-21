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

authenticator = stauth.Authenticate(credentials, "sbh_cookie_v3", "key_v3_999", 30)

# --- 3. HELFER FUNCTIONS ---
def save_log(file, data):
    df = pd.DataFrame([data])
    if not os.path.exists(file):
        df.to_csv(file, index=False)
    else:
        df.to_csv(file, mode='a', header=False, index=False)

def get_response_mock(model_key, prompt, filename=None):
    time.sleep(1.2) 
    model_name = MODELS[model_key]['name']
    prefix = f"**{model_name}**: "
    
    # Dateianalyse simulieren
    file_msg = ""
    if filename:
        file_msg = f"\n\n*Ich habe das Dokument '{filename}' analysiert.* "
    
    raw_responses = [
        f"Das ist eine wichtige Frage.{file_msg} Hier sind die Kernpunkte:\n1. Analyse der Daten\n2. Strategische Ausrichtung\n3. Umsetzung",
        f"Moin!{file_msg} Basierend auf deiner Eingabe schlage ich vor, dass wir Option B wählen.",
        f"Hier ist der Entwurf.{file_msg} Ich habe dabei besonders auf die Vorgaben der SBH geachtet."
    ]
    full_response = prefix + random.choice(raw_responses)
    
    in_tok = len(prompt) * 2 + (500 if filename else 0)
    out_tok = random.randint(100, 400)
    
    return full_response, in_tok, out_tok

def calc_cost(model, in_tok, out_tok):
    return (in_tok/1e6 * MODELS[model]["input"]) + (out_tok/1e6 * MODELS[model]["output"])

# --- 4. FEEDBACK DIALOG (POPUP) ---
@st.dialog("Wie war das Ergebnis?")
def feedback_modal(user, model):
    st.write("Dein Feedback hilft uns bei der Modellauswahl.")
    
    # Sterne Bewertung
    rating = st.feedback("stars")
    comment = st.text_input("Kurzer Kommentar (Optional)")
    
    if st.button("Bewertung senden"):
        if rating is not None:
            final_rating = rating + 1
            save_log("feedback.csv", {
                "time": datetime.now().strftime("%H:%M:%S"), 
                "user": user, 
                "model": model, 
                "rating": final_rating, 
                "comment": comment
            })
            st.success("Gespeichert!")
            time.sleep(0.5)
            st.session_state
