import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import os
import time
import random
from datetime import datetime

# --- ECHTE API CLIENTS ---
import google.generativeai as genai
from openai import OpenAI
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
import anthropic
from groq import Groq

# --- 0. PAGE CONFIG ---
st.set_page_config(page_title="LLM Pilot", page_icon="🤖", layout="wide")

# --- 1. CONFIG ---
MOCK_MODE = True 

USERS = {
    "michael.soth": {"name": "Michael Soth", "password": "Start123!", "email": "michael.soth@sbh.hamburg.de"},
    "tester":       {"name": "Test User",    "password": "Start123!", "email": "team@sbh.hamburg.de"}
}

# DAS 6-MODELLE-PORTFOLIO
MODELS = {
    "gemini-1.5-flash": {
        "name": "Google Gemini Flash ⚡", "provider": "google", "input": 0.10, "output": 0.40
    },
    "gemini-1.5-pro": {
        "name": "Google Gemini Pro 🧠", "provider": "google", "input": 1.25, "output": 5.00
    },
    "gpt-4o": {
        "name": "OpenAI GPT-4o 🚀", "provider": "openai", "input": 2.50, "output": 10.00
    },
    "mistral-large-latest": {
        "name": "Mistral Large (EU) 🇪🇺", "provider": "mistral", "input": 2.00, "output": 6.00
    },
    "claude-3-5-sonnet-20240620": {
        "name": "Claude 3.5 Sonnet ✍️", "provider": "anthropic", "input": 3.00, "output": 15.00
    },
    "llama3-70b-8192": {
        "name": "Llama 3 (via Groq) 🏎️", "provider": "groq", "input": 0.59, "output": 0.79
    }
}

# --- 2. AUTH ---
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

authenticator = stauth.Authenticate(credentials, "sbh_cookie_v5", "key_v5_sixmodels", 30)

# --- 3. LOGIC ---
def get_api_key(provider):
    try:
        return st.secrets["api_keys"][provider]
    except:
        return None

def get_llm_response(model_key, messages_history, file_content=None):
    conf = MODELS[model_key]
    provider = conf["provider"]
    
    # --- MOCK SIMULATION ---
    if MOCK_MODE:
        time.sleep(1.0 if provider != "groq" else 0.2) # Groq ist schneller!
        prefix = f"**[MOCK {conf['name']}]:** "
        last_prompt = messages_history[-1]["content"]
        
        file_msg = ""
        if file_content: file_msg = "\n*(Datei-Analyse simuliert)*"
        
        resp = f"{prefix}Antwort auf '{last_prompt}'... {file_msg}\n\nHier würde das echte Modell antworten."
        return resp, len(last_prompt), 150

    # --- REAL MODE ---
    else:
        api_key = get_api_key(provider)
        if not api_key: return f"⚠️ Key für {provider} fehlt!", 0, 0
        
        try:
            # 1. GOOGLE
            if provider == "google":
                genai.configure(api_key=api_key)
                google_hist = []
                for m in messages_history[:-1]:
                    role = "user" if m["role"] == "user" else "model"
                    google_hist.append({"role": role, "parts": [m["content"]]})
                model = genai.GenerativeModel(model_key)
                chat = model.start_chat(history=google_hist)
                last_msg = messages_history[-1]["content"]
                if file_content: last_msg += f"\n\nDokument:\n{file_content[:10000]}"
                resp = chat.send_message(last_msg)
                return resp.text, model.count_tokens(last_msg).total_tokens, model.count_tokens(resp.text).total_tokens

            # 2. OPENAI
            elif provider == "openai":
                client = OpenAI(api_key=api_key)
                msgs = list(messages_history)
                if file_content: msgs[-1]["content"] += f"\n\nDokument:\n{file_content[:10000]}"
                resp = client.chat.completions.create(model=model_key, messages=msgs)
                return resp.choices[0].message.content, resp.usage.prompt_tokens, resp.usage.completion_tokens

            # 3. MISTRAL
            elif provider == "mistral":
                client = MistralClient(api_key=api_key)
                m_msgs = []
                for m in messages_history:
                    c = m["content"]
                    if m == messages_history[-1] and file_content: c += f"\n\nDokument:\n{file_content[:10000]}"
                    m_msgs.append(ChatMessage(role=m["role"], content=c))
                resp = client.chat(model=model_key, messages=m_msgs)
                return resp.choices[0].message.content, resp.usage.prompt_tokens, resp.usage.completion_tokens

            # 4. ANTHROPIC (CLAUDE)
            elif provider == "anthropic":
                client = anthropic.Anthropic(api_key=api_key)
                # Claude mag keine System-Rolle in der History, wir nutzen einfaches Mapping
                # Für diesen Pilot senden wir nur den Prompt + File, um History-Errors zu vermeiden (simpel)
                last_msg = messages_history[-1]["content"]
                if file_content: last_msg += f"\n\nDokument:\n{file_content[:10000]}"
                
                message = client.messages.create(
                    model=model_key,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": last_msg}]
                )
                # Token Usage bei Claude ist im Header, hier vereinfacht:
                return message.content[0].text, message.usage.input_tokens, message.usage.output_tokens

            # 5. GROQ (LLAMA)
            elif provider == "groq":
                client = Groq(api_key=api_key)
                msgs = list(messages_history)
                if file_content: msgs[-1]["content"] += f"\n\nDokument:\n{file_content[:10000]}"
                resp = client.chat.completions.create(model=model_key, messages=msgs)
                return resp.choices[0].message.content, resp.usage.prompt_tokens, resp.usage.completion_tokens

        except Exception as e:
            return f"❌ Fehler bei {provider}: {e}", 0, 0
    
    return "Error", 0, 0

def calc_cost(model_key, in_tok, out_tok):
    m = MODELS[model_key]
    return (in_tok/1e6 * m["input"]) + (out_tok/1e6 * m["output"])

def save_log(file, data):
    df = pd.DataFrame([data])
    if not os.path.exists(file):
        df.to_csv(file, index=False)
    else:
        df.to_csv(file, mode='a', header=False, index=False)

# --- 4. FEEDBACK MODAL ---
@st.dialog("⭐ Feedback")
def feedback_modal(user, model):
    st.write(f"Wie war **{model}**?")
    rating = st.feedback("stars")
    comment = st.text_input("Kommentar")
    if st.button("Senden"):
        if rating is not None:
            save_log("feedback.csv", {"time": datetime.now().strftime("%H:%M:%S"), "user": user, "model": model, "rating": rating+1, "comment": comment})
            st.toast("Danke!", icon="✅")
            time.sleep(0.5)
            st.session_state.show_feedback = False
            st.rerun()

# --- 5. MAIN APP ---
authenticator.login()

if st.session_state["authentication_status"]:
    user_id = st.session_state["username"]
    
    if "messages" not in st.session_state: st.session_state.messages = []
    if "show_feedback" not in st.session_state: st.session_state.show_feedback = False
    if "last_model" not in st.session_state: st.session_state.last_model = ""

    # SIDEBAR
    with st.sidebar:
        st.header("⚙️ Setup")
        st.write(f"User: **{USERS[user_id]['name']}**")
        
        page = "Chat"
        if user_id == "michael.soth":
            st.divider()
            page = st.radio("Menü", ["💬 Chat", "📊 Admin"])
        
        if page == "💬 Chat":
            st.divider()
            sel_model = st.selectbox("Modell:", list(MODELS.keys()), format_func=lambda x: MODELS[x]["name"])
            
            uploaded_file = st.file_uploader("Dokument:", type=["txt","csv","py","md"])
            file_text = None
            if uploaded_file:
                try: file_text = uploaded_file.getvalue().decode("utf-8"); st.success("Datei gelesen!")
                except: st.error("Nur Text-Dateien im Pilot!")
            
            st.divider()
            if st.button("🗑️ Reset", type="primary"):
                st.session_state.messages = []; st.session_state.show_feedback = False; st.rerun()

        st.divider()
        authenticator.logout('Logout', 'sidebar')

    # VIEW 1: CHAT
    if page == "💬 Chat":
        st.title("🤖 LLM Pilot")
        if MOCK_MODE: st.warning("⚠️ MOCK MODE - Keine echten Daten/Kosten")

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
                st.markdown(msg["content"])
                if "stats" in msg: st.caption(msg["stats"])

        if prompt := st.chat_input("Deine Nachricht..."):
            display_prompt = prompt + (f" [Anhang: {uploaded_file.name}]" if file_text else "")
            st.session_state.messages.append({"role": "user", "content": display_prompt})
            with st.chat_message("user", avatar="👤"): st.write(display_prompt)

            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Arbeite..."):
                    resp, in_t, out_t = get_llm_response(sel_model, st.session_state.messages, file_text)
                    cost = calc_cost(sel_model, in_t, out_t)
                    st.markdown(resp)
                    stats = f"Kosten: ${cost:.5f}"
                    st.caption(stats)
                    st.session_state.messages.append({"role": "assistant", "content": resp, "stats": stats})
                    save_log("usage.csv", {"time": datetime.now().strftime("%H:%M:%S"), "user": user_id, "model": sel_model, "cost": cost})
                    
                    st.session_state.show_feedback = True
                    st.session_state.last_model = sel_model
                    st.rerun()

        if st.session_state.show_feedback:
            feedback_modal(user_id, MODELS[st.session_state.last_model]["name"])

    # VIEW 2: ADMIN
    elif page == "📊 Admin":
        st.title("Admin Cockpit")
        if os.path.exists("usage.csv"):
            df = pd.read_csv("usage.csv")
            c1, c2 = st.columns(2)
            c1.metric("Gesamt ($)", f"{df['cost'].sum():.4f}")
            c2.metric("Prompts", len(df))
            st.bar_chart(df.groupby("model")["cost"].sum())
            st.dataframe(df.sort_values("time", ascending=False))
        else: st.info("Keine Daten")

elif st.session_state["authentication_status"] is False: st.error('Falsch')
elif st.session_state["authentication_status"] is None: st.warning('Bitte einloggen')
