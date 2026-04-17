import streamlit as st
from google import genai
from PIL import Image
import os
import re
from pypdf import PdfReader

# =========================
# INICIAL
# =========================
st.set_page_config(page_title="ROMANO v6.0", layout="wide", page_icon="⚔️")

# Inicialização do Cliente API
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Erro: GEMINI_API_KEY não configurada nos Secrets.")
 = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

# das bases
BASE_CONHECIMENTO_DIR = "base_conhecimento"
PASTA_LEGISLACAO = os.path.join(BASE_CONHECIMENTO_DIR, "legislacao_sp")
PASTA_ITS = os.path.join(BASE_CONHECIMENTO_DIR, "its_sp")

# Garantir que as pastas existam para não dar erro de leitura
for p in [PASTA_LEGISLACAO, PASTA_ITS]:
    if not exist_ok=True)

# FUNÇÕES TÉCNICO
# =========================

def extrair_texto_pdf(caminho_arquivo):
    try:
        reader = PdfReader(caminho_arquivo)
        return "\n".join([p.extract_text() for p in reader.pages    except Exception:
        return carregar_base_local():
    base = []
    pastas = [("legislacao_sp", PASTA_LEGISLACAO), ("its_sp", PASTA_ITS)]
    for tipo, pasta in        for nome_arquivo in os.listdir(pasta):
    if nome_arquivo.lower().endswith(".pdf"):
                caminho = os.path.join(pasta, nome_arquivo)
                texto = extrair_texto_pdf(caminho)
                base.append({
                    "tipo": tipo, "arquivo": nome_arquivo,
                    "texto": texto, "texto_lower": texto.lower()
                })
    return base

def buscar_na_base(pergunta, top_k=2):
    base    pergunta_lower = pergunta.lower()
    termos = [t for pergunta_lower) if len(t)  
    resultados = []
   in base:
        score = sum(3 for t in termos if t in item["arquivo"].lower())
 for t in termos if t in item["texto_lower"])
        if 0:
     score, "arquivo": item["arquivo"], "texto": item["texto"]})
    
    return sorted(resultados, key=lambda x: x["score"], reverse=True)[:top_k]

# =========================
# PROMPT DO (PERSONALIDADE ROMANO)
# =========================
PROMPT_SISTEMA = """
Você é ROMANO v6.0, desenvolvido pelo Grupo ROMANO.IA. Representação: Gladiador com autoridade, respeito técnica.
Especialista em: Engenharia Civil, Segurança Contra Incêndio (PMESP), Nutrição, e Música.

REGRAS CRÍTICAS:
1. Resposta instantânea e direta. Sem "Olá" ou "Fico feliz".
2. Use o Decreto Estadual nº 63.911/18 e as ITs de SP como fonte primária.
3. Se o dado for inconclusivo, a lógica técnica mais provável.
4. Responda em Português Brasileiro. Use Markdown.
"""

# =========================
# RESPOSTA
# =========================

def imagem=None):
    contexto_extra  resultados = buscar_na_base(pergunta)
    
    if resultados:
        contexto_extra = "\n\nCONTEXTO TÉCNICO ENCONTRADO NA BASE:\n"
        for r in resultados:
            contexto_extra += f"--- ---\n{r['texto'][:2000]}\n"

    prompt_final = f"{PROMPT_SISTEMA}\n{contexto_extra}\n\nPERGUNTA DO COMANDANTE: {pergunta}"

        if imagem:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt_final, imagem])
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt_final)
        return response.text
    except Exception as e:
  f"Erro técnico na legião: =========================
# INTERFACE STREAMLIT
# =========================

# CSS para Estilização    <style>
    .main { background-color: #f5f5f5; }
    .stChatMessage { border-radius: 10px; border: 1px solid #ddd; }
 { border-top: 2px solid #8B0000; }
    h1 { color: #8B0000; font-family: 'Times New Roman'; font-weight: bold; }
    </style>
    """, ROMANO v6.0 - Sistema de Comando")

if "messages"    st.session_state.messages = []

# Sidebar para Upload de Imagens e Documentos
with st.sidebar:
 de Campo")
 = st.file_uploader("Enviar Planta ou Foto", type=['png', 'jpg', 'jpeg'])
    img_input = Image.open(img_file) if img_file else None
 st.image(img_input, caption="Visualizado pelo Gladiador")

# Mostrar histórico
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input do Usuário
if st.chat_input("Ordene, Comandante..."):
 "user", "content":    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando Decretos            full_response img_input)
            st.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
