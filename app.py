import streamlit as st
import google.generativeai as genai
import os

# Configuração da Página
st.set_page_config(page_title="ROMANUS", layout="centered")

# Estilização CSS para o título e layout
st.markdown("""
    <style>
    .main-title {
        font-size: 50px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 30px;
        color: #FFFFFF;
    }
    /* Ajuste para evitar sobreposição no chat */
    .stChatMessage {
        margin-bottom: 10px;
    }
    footer {visibility: hidden;}
    </style>
    <div class="main-title">ROMANUS</div>
    """, unsafe_allow_html=True)

# Inicialização do Modelo (Configuração da API)
# Certifique-se de que a variável de ambiente GOOGLE_API_KEY esteja configurada no GitHub Secrets/Streamlit Cloud
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    # Fallback para desenvolvimento local caso não use secrets
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    else:
        st.error("Erro: API Key não encontrada. Configure GOOGLE_API_KEY nas Secrets.")
        st.stop()

# Inicialização do st.session_state (Requisito 4)
if "chat_session" not in st.session_state:
    model = genai.GenerativeModel("gemini-1.5-flash")
    st.session_state.chat_session = model.start_chat(history=[])

if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibição do Histórico de Mensagens (Requisito 3 e 5)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Área de Input do Chat
if prompt := st.chat_input("Digite sua mensagem..."):
    # Adiciona mensagem do usuário ao histórico da interface
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Processamento da Resposta da IA
    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(prompt)
            full_response = response.text
            st.markdown(full_response)
            
            # Adiciona resposta ao histórico da interface
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"Erro ao processar resposta: {e}")

