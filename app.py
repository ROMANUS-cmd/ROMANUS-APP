import streamlit as st
import os
import re
from PdfReader

# =========================================================
# CONFIGURAÇÃO DE INTERFACE - ROMANO v6.0
# =========================================================
st.set_page_config(page_title="ROMANO v6.0", layout="wide")

st.markdown("<h1 style='color: #8B0000;'>⚔️ ROMANO v6.0</h1>", unsafe_allow_html=True)

# Definição da Base de Dados Local
PASTA_BASE = "base_conhecimento"
if not os.path.exists(PASTA_BASE):
    os.makedirs(PASTA_BASE)

# =========================================================
# TÉCNICAS (MODO LOCAL)
# =========================================================

@st.cache_data
def carregar_e_ler_banco():
    banco = []
    for arquivo in os.listdir(PASTA_BASE):
        if arquivo.lower().endswith(".pdf"):
            caminho = os.path.join(PASTA_BASE,            try:
                reader = PdfReader(caminho)
                texto = " ".join([p.extract_text() for p in reader.pages if p.extract_text()])
                banco.append({"nome": arquivo, "texto": texto})
            except:
                continue
    return banco

# Inicialização
banco_dados = carregar_e_ler_banco()

if not in st.session_state:
    st.session_state.messages = []

# Exibição
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# BARRA DE DIGITAÇÃO
if prompt := st.chat_input("Comandante, ordene a busca no banco de dados..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Lógica de Pesquisa        termos = prompt.lower().split()
        achados = [doc for doc in banco_dados if any(t in doc['texto'].lower() for t in termos)]
        
        if achados:
            doc = achados[0]
            resposta = f"**RELATÓRIO TÉCNICO LOCAL:**\n\n**Arquivo:** `{doc['nome']}`\n\n**Conteúdo:**\n{doc['texto'][:1500]}..."
        else:
            resposta = "Comandante, a informação não consta nos documentos da pasta 'base_conhecimento'."
            
        st.markdown(resposta)
        st.session_state.messages.append({"role": "assistant", "content": resposta})
