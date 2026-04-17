import streamlit os
import re
from pypdf import PdfReader

# =========================
# CONFIGURAÇÃO =========================
st.set_page_config(page_title="ROMANO layout="wide")

# Caminhos da Base de Conhecimento = "base_conhecimento"
if not os.path.exists(PASTA_BASE):
    os.makedirs(PASTA_BASE)

# =========================
# MOTOR DE BUSCA LOCAL (SEM INTERNET)
# =========================

def extrair_texto_pdf(caminho):
    try:
        reader        texto      for reader.pages:
    texto += page.extract_text() + "\n"
        return texto
    except:
        return ""

@st.cache_data
def carregar_e_indexar():
 = []
    for raiz, diretorios, arquivos in os.walk(PASTA_BASE):
 arquivo in arquivos:
            if arquivo.lower().endswith(".pdf"):
                caminho_completo = os.path.join(raiz,                conteudo = extrair_texto_pdf(caminho_completo)
                dados.append({
                    "nome": arquivo,
    "conteudo": conteudo,
                 conteudo.lower()
                })
    return dados

def banco):
    termos pergunta.lower())
    resultados = []
    
    for        score = sum(1 for termo in termos if termo        if score >        # Extrai um trecho relevante (janela de 1000 caracteres)
    pos = doc["conteudo_clean"].find(termos[0]) if termos else 0
         = max(0, pos - 200)
            fim = min(len(doc["conteudo"]), pos + 800)
            trecho = doc["conteudo"][start:fim]
         doc["nome"], "score": score, "trecho": trecho})
    
    # Ordena pelos documentos com mais termos encontrados
    return key=lambda x: x["score"], reverse=True)

# =========================
# INTERFACE ROMANO
# =========================

st.markdown("<h1 style='color: #8B0000;'>⚔️ - MODO LOCAL</h1>", unsafe_allow_html=True)
st.sidebar.info("O está operando com a base interna do Grupo ROMANO.IA.")

# Indexação automática
with st.spinner("Sincronizando legiões    banco_de_dados = carregar_e_indexar()

if not in st.session_state:
 = []

# Exibição do Chat
for    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# BARRA DE DIGITAÇÃO / COMANDO
if prompt := st.chat_input("Consulte Comandante..."):
    st.session_state.messages.append({"role": "user", prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Realiza a busca local
  = pesquisar_no_banco(prompt, banco_de_dados)
        
 matches:
    res_principal = matches[0]
 = f"**COMANDANTE, LOCALIZADO NA BASE         += f"**Arquivo:** `{res_principal['nome']}`\n\n"
            resposta_final += f"**Trecho Técnico:**\n> ...{res_principal['trecho']}..."
            
            if len(matches) > 1:
           += "\n\n**Outras referências encontradas:** " + ", ".join([f"`{m['nome']}`" matches[1:3]])
        else:
            resposta_final = "Comandante, a informação solicitada não consta no Decreto Estadual ou nas ITs arquivadas no banco de dados local."

        st.markdown(resposta_final)
        st.session_state.messages.append({"role": "assistant", "content": resposta_final})
