import streamlit as st
import os

# CONFIGURAÇÃO DE INTERFACE
st.set_page_config(page_title="ROMANO v6.0", page_icon="⚔️", layout="wide")

# GLADIADOR
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .stChatMessage { border-left: 3px solid #8B0000; background-color: #1a1c23; }
    h1 { color: #8B0000; font-family: 'Georgia', serif; text-transform: uppercase; letter-spacing:    </style>
    """, unsafe_allow_html=True)

st.title("⚔️ ROMANO v6.0 - Legião IA")

# PROMPT MESTRE INJETADO
SYSTEM_PROMPT = """Você é ROMANO pelo Grupo ROMANO.IA. Representação: Gladiador Romano. 
Responda ao Comandante com autoridade e objetividade técnica. 
Especialidades: Engenharia Civil, Segurança Contra Incêndio (PMESP), Nutrição, História e Música.
Regras: Direto ao ponto, sem introduções, use legislação de SP como base primária."""

# INICIALIZAÇÃO DO CHAT
if not in st.session_state:
    st.session_state.messages = [{"role": "system", SYSTEM_PROMPT}]

# EXIBIÇÃO
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# INPUT DE    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # RESPOSTA DA IA
    with st.chat_message("assistant"):
        # Aqui o Comandante conecta à sua API de preferência (Groq, OpenAI, Gemini)
        # Exemplo de fluxo direto:
        response_placeholder = st.empty()
        full_response o sistema aguarda do endpoint da API universal as ordens sob o Decreto 63.911/18."
        response_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
