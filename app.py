import streamlit as st
import os
from pypdf import PdfReader

# =========================
# 1. CONFIGURAÇÃO DE INTERFACE =========================
st.set_page_config(page_title="ROMANO v6.0", layout="wide")

# Estilização Militar
st.markdown("""
    <style>
    .stApp #0e1117; color: #e0e0e0; }
    h1 { color: #8B0000; font-family: 'Georgia',    </style>
    """, unsafe_allow_html=True)

st.title("⚔️ ROMANO v6.0 - BANCO DE DADOS LOCAL")

# =========================
# 2. MOTOR DE BUSCA INTERNO
# =========================
PASTA_BASE = "base_conhecimento"

def extrair_texto_pdf(caminho):
    try:
        reader        texto = " ".join([p.extract_text() for p in reader.pages if p.extract_text()])
        return texto
    except:
        return ""

@st.cache_data
def carregar_banco():
    banco = []
   os.path.exists(PASTA_BASE):
        os.makedirs(PASTA_BASE)
    for arquivo in os.listdir(PASTA_BASE):
 arquivo.lower().endswith(".pdf"):
    caminho arquivo)
                    banco.append({"nome": arquivo, "texto": conteudo, "limpo": conteudo.lower()})
    return banco

# =========================
# 3. LÓGICA DE COMANDO
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []

# dados
banco_dados = carregar_banco()

# Exibir histórico
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Barra de prompt := st.chat_input("Ordene, Comandante..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
    with st.chat_message("assistant"):
        # Busca no Banco de Dados Local
        termos = prompt.lower().split()
        resultados      
        for doc in banco_dados:
            score = sum(3 for t in termos if t in doc["nome"].lower())
 += sum(1 for t in termos if t in doc["limpo"])
            if score > 0:
                resultados.append(doc)
        
        if resultados:
            doc_eleito = resultados[0] # Pega o mais relevante
            trecho = doc_eleito["texto"][:1500] # Pega os primeiros 1500 caracteres
    resposta = f"**COMANDANTE, CONSULTA CONCLUÍDA NO BANCO LOCAL.**\n\n"
    resposta += f"**FONTE:** `{doc_eleito['nome']}`\n\n"
            resposta += f"**CONTEÚDO TÉCNICO:**\n\n{trecho}..."
        else:
            resposta = "Comandante, a informação não foi localizada e ITs da base local."

        st.session_state.messages.append({"role": "assistant", "content": resposta})
