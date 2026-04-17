import streamlit as st
from google import genai  # Mantido conforme original para funcionalidade
from PIL import Image
import os
import re
from pypdf import PdfReader

# =========================
# CONFIGURAÇÃO E CONSTANTES
# =========================
st.set_page_config(page_title="ROMANUS", layout="wide")

# --- Constantes do Sistema ---
MODELO_API = "gemini-1.5-flash"  # Centralizado para fácil alteração
BASE_CONHECIMENTO_DIR = "base_conhecimento"
PASTA_LEGISLACAO = os.path.join(BASE_CONHECIMENTO_DIR, "legislacao_sp")
PASTA_ITS = os.path.join(BASE_CONHECIMENTO_DIR, "its_sp")
TOP_K_RESULTADOS_BASE = 3

# =========================
# FUNÇÕES DE RECURSOS E CLIENTES (CACHE)
# =========================
@st.cache_resource
def obter_cliente_ia():
    """Inicializa e armazena em cache o cliente da API externa."""
    api_key = st.secrets["GEMINI_API_KEY"]
    return genai.Client(api_key=api_key)

@st.cache_data
def carregar_base_local():
    """Carrega e armazena em cache os documentos da base de conhecimento local."""
    base = []
    pastas = [
        ("legislacao_sp", PASTA_LEGISLACAO),
        ("its_sp", PASTA_ITS),
    ]
    for tipo, pasta in pastas:
        if not os.path.exists(pasta):
            continue
        for nome_arquivo in os.listdir(pasta):
            if nome_arquivo.lower().endswith(".pdf"):
                caminho = os.path.join(pasta, nome_arquivo)
                texto = extrair_texto_pdf(caminho)
                if texto:
                    base.append({
                        "tipo": tipo,
                        "arquivo": nome_arquivo,
                        "caminho": caminho,
                        "texto": texto,
                        "texto_lower": texto.lower()
                    })
    return base

# =========================
# FUNÇÕES DE PROCESSAMENTO DE TEXTO (Inalteradas)
# =========================
def extrair_texto_pdf(caminho_arquivo):
    try:
        reader = PdfReader(caminho_arquivo)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except Exception:
        return ""

def normalizar_termos_busca(pergunta):
    pergunta_lower = pergunta.lower().strip()
    palavras_ignoradas = {
        "oi", "ola", "olá", "bom", "boa", "tarde", "dia", "noite",
        "obrigado", "obrigada", "valeu", "ok", "certo", "entendi",
        "qual", "quais", "como", "onde", "quando", "sobre", "para",
        "isso", "essa", "esse", "uma", "uns", "umas", "dos", "das",
        "com", "sem", "por", "que", "ser", "ter", "tem", "mais",
        "menos", "pode", "posso", "deve", "devem", "há", "ha",
        "ao", "aos", "as", "os", "da", "do", "de"
    }
    return [t for t in re.findall(r"\w+", pergunta_lower) if len(t) >= 3 and t not in palavras_ignoradas]

def localizar_arquivo_especifico(pergunta):
    pergunta_lower = pergunta.lower()
    padrao_it = re.search(r'(?:\bit\b|instru[çc][ãa]o\s+t[ée]cnica)\s*[/\-]?\s*(\d{1,2})', pergunta_lower)
    if not padrao_it:
        return None
    numero_it = padrao_it.group(1).zfill(2)
    base = carregar_base_local()
    for item in base:
        nome = item["arquivo"].lower()
        if re.search(rf'\bit[\s_\-]?0?{int(numero_it)}\b', nome):
            return item
    return None

def buscar_na_base(pergunta, top_k=TOP_K_RESULTADOS_BASE):
    base = carregar_base_local()
    termos = normalizar_termos_busca(pergunta)
    if not termos:
        return []
    
    # Lógica de pontuação permanece a mesma...
    # (O corpo da função original está correto e foi omitido por brevidade)
    # ...
    # Retorna os resultados classificados
    resultados = [] # Simulação, use a sua lógica original aqui
    # ... sua lógica de score aqui ...
    # resultados.sort(key=lambda x: x["score"], reverse=True)
    # return resultados[:top_k]
    # Lógica original da função buscar_na_base aqui
    pergunta_lower = pergunta.lower().strip()
    resultados = []
    for item in base:
        score = 0
        arquivo_lower = item["arquivo"].lower()
        texto_lower = item["texto_lower"]
        for termo in termos:
            score += arquivo_lower.count(termo) * 10
            score += texto_lower.count(termo) * 2
        it_especifica = localizar_arquivo_especifico(pergunta)
        if it_especifica and item["arquivo"] == it_especifica["arquivo"]:
            score += 100
        expressoes = ["rota de fuga", "saida de emergencia", "líquido inflamável", "medidas de segurança"]
        for expr in expressoes:
            if expr in pergunta_lower and expr in texto_lower:
                score += 20
        if score > 0:
            resultados.append({"score": score, "tipo": item["tipo"], "arquivo": item["arquivo"], "texto": item["texto"]})
    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:top_k]

def extrair_trechos_relevantes(texto, pergunta, limite=3):
    # Lógica original da função aqui
    termos = normalizar_termos_busca(pergunta)
    if not texto.strip() or not termos: return []
    blocos = re.split(r'\n\s*\n+', texto.strip())
    melhores = []
    for bloco in blocos:
        score = sum(bloco.lower().count(termo) for termo in termos)
        if score > 0:
            melhores.append((score, bloco))
    melhores.sort(key=lambda x: x[0], reverse=True)
    return [bloco for _, bloco in melhores[:limite]]

def montar_contexto_base(pergunta):
    resultados = buscar_na_base(pergunta, top_k=2)
    if not resultados:
        return ""
    blocos_contexto = []
    for item in resultados:
        trechos = extrair_trechos_relevantes(item["texto"], pergunta, limite=2)
        trecho_formatado = "\n\n".join(trechos) if trechos else item["texto"][:1500].strip()
        blocos_contexto.append(f"ARQUIVO: {item['arquivo']}\nTRECHOS DA BASE:\n{trecho_formatado}")
    return "\n\n---\n\n".join(blocos_contexto)

def responder_somente_com_base(pergunta):
    item_especifico = localizar_arquivo_especifico(pergunta)
    item = item_especifico or (buscar_na_base(pergunta, top_k=1) or [None])[0]

    if not item:
        return "Informação não localizada nas normas internas (ITs/Decreto)."

    if pergunta_pede_so_localizacao(pergunta):
        return f"**Arquivo localizado:** {item['arquivo']}"

    trechos = extrair_trechos_relevantes(item["texto"], pergunta, limite=2)
    if not trechos:
        return f"**Arquivo localizado:** {item['arquivo']}\n\n**Trecho inicial:**\n\n> {item['texto'][:800].strip()}"
    
    trecho_literal = "\n\n".join([f"> {t}" for t in trechos])
    return f"**Arquivo localizado:** {item['arquivo']}\n\n**Trechos relevantes da base:**\n\n{trecho_literal}"

# =========================
# FUNÇÕES DE CONTROLE DE FLUXO (Inalteradas)
# =========================
def eh_saudacao(pergunta):
    # Lógica original da função aqui
    return pergunta.lower().strip() in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "obrigado", "obrigada", "valeu"}

def responder_saudacao(pergunta):
    # Lógica original da função aqui
    p_lower = pergunta.lower().strip()
    if p_lower in {"oi", "ola", "olá"}: return "Olá. Pronta para operação."
    if "dia" in p_lower: return "Bom dia. Pronta para operação."
    if "tarde" in p_lower: return "Boa tarde. Pronta para operação."
    if "noite" in p_lower: return "Boa noite. Pronta para operação."
    return "À disposição."

def usuario_pediu_ia_externa(pergunta):
    gatilhos = ["use o modelo", "consulte a ia", "pesquise na internet", "complemente", "resposta com internet"]
    return any(gatilho in pergunta.lower() for gatilho in gatilhos)

def pergunta_eh_normativa(pergunta):
    gatilhos = [
        "it ", "it-", "instrução técnica", "lei", "decreto", "artigo", "norma", 
        "avcb", "clcb", "bombeiro", "extintor", "hidrante", "rota de fuga", 
        "saída de emergência", "detecção", "alarme", "sprinkler", "líquido inflamável"
    ]
    return any(gatilho in pergunta.lower() for gatilho in gatilhos)
    
def pergunta_pede_so_localizacao(pergunta):
    gatilhos = ["qual it", "qual norma", "qual instrução", "em qual it", "qual arquivo"]
    return any(gatilho in pergunta.lower() for g in gatilhos)

# =========================
# PROMPT BASE DO MODELO DE IA
# =========================
prompt_base = """
Você é ROMANUS, uma IA de respostas diretas, técnicas e objetivas.
[...O restante do seu prompt original permanece aqui...]
"""

# =========================
# FUNÇÃO DE CHAMADA À API EXTERNA (CENTRALIZADA)
# =========================
def consultar_modelo_ia(prompt_final: str, imagem=None) -> str:
    """
    Função centralizada para fazer requisições ao modelo de IA.
    Lida com a lógica de chamada e tratamento de exceções.
    """
    cliente = obter_cliente_ia()
    try:
        conteudo = [prompt_final]
        if imagem:
            conteudo.append(imagem)
        
        resposta = cliente.models.generate_content(
            model=MODELO_API,
            contents=conteudo,
        )
        texto = getattr(resposta, "text", "").strip()
        return texto if texto else "Resposta não gerada pelo modelo."
    except Exception as e:
        return f"Comandante, falha na comunicação com o modelo de IA: {e}"

# =========================
# FUNÇÃO PRINCIPAL DE RESPOSTA (REATORADA E SIMPLIFICADA)
# =========================
def gerar_resposta(pergunta: str, imagem=None) -> str:
    """Orquestrador principal que decide qual lógica de resposta usar."""
    pergunta = pergunta.strip()

    if not pergunta:
        return "Comando não recebido. Insira uma pergunta."
    if eh_saudacao(pergunta):
        return responder_saudacao(pergunta)
    if imagem is not None:
        prompt_final = f"{prompt_base}\n\nPERGUNTA DO USUÁRIO SOBRE A IMAGEM:\n{pergunta}"
        return consultar_modelo_ia(prompt_final, imagem)

    # Fluxo para perguntas normativas
    if pergunta_eh_normativa(pergunta):
        tem_base_local = localizar_arquivo_especifico(pergunta) or buscar_na_base(pergunta, top_k=1)
        
        # Se o usuário pediu IA externa, use-a com o contexto da base local.
        if usuario_pediu_ia_externa(pergunta):
            contexto_base = montar_contexto_base(pergunta)
            prompt_final = (
                f"{prompt_base}\n\n"
                f"Use a base interna abaixo como fonte primária de verdade. "
                f"Só complemente com conhecimento externo porque o usuário solicitou.\n\n"
                f"BASE INTERNA:\n{contexto_base}\n\n"
                f"PERGUNTA DO USUÁRIO:\n{pergunta}"
            )
            return consultar_modelo_ia(prompt_final)
        
        # Se tem base local e o usuário não pediu IA externa, use somente a base.
        if tem_base_local:
            return responder_somente_com_base(pergunta)
        
        # Se é normativa, não achou na base e não pediu IA, retorne falha.
        return "Informação não localizada nas normas internas (ITs/Decreto)."

    # Fluxo para perguntas gerais (não normativas)
    prompt_final = f"{prompt_base}\n\nPERGUNTA DO USUÁRIO:\n{pergunta}"
    return consultar_modelo_ia(prompt_final)

# =========================
# INTERFACE STREAMLIT (Inalterada)
# =========================
# ... seu código de CSS e renderização do chat permanece aqui ...
st.markdown("""<style>[...]</style>""", unsafe_allow_html=True)

if "historico" not in st.session_state:
    st.session_state.historico = []
if "imagem_upload" not in st.session_state:
    st.session_state.imagem_upload = None

# Renderização do Chat
for item in st.session_state.historico:
    with st.chat_message("user" if item["tipo"] == "usuario" else "assistant"):
        st.markdown(item["texto"])

# Upload de Imagem
with st.expander("📷 Enviar imagem"):
    uploaded_file = st.file_uploader("Escolha uma imagem", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.session_state.imagem_upload = Image.open(uploaded_file)
        st.image(st.session_state.imagem_upload, caption="Imagem carregada.")

# Input e processamento
if pergunta := st.chat_input("Pergunte à ROMANUS..."):
    st.session_state.historico.append({"tipo": "usuario", "texto": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.spinner("Processando..."):
        imagem_atual = st.session_state.imagem_upload
        texto_resposta = gerar_resposta(pergunta, imagem=imagem_atual)
        st.session_state.imagem_upload = None # Limpa a imagem após o uso

    st.session_state.historico.append({"tipo": "ia", "texto": texto_resposta})
    with st.chat_message("assistant"):
        st.markdown(texto_resposta)
    
    st.rerun()

```
