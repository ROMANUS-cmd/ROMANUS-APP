import streamlit as st
from google import genai
from PIL import Image
import os
import re
from pypdf import PdfReader

# Configuração da Página
st.set_page_config(page_title="ROMANUS", layout="wide")

# Inicialização da API Gemini
api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

# Caminhos da Base de Conhecimento
BASE_CONHECIMENTO_DIR = "base_conhecimento"
PASTA_LEGISLACAO = os.path.join(BASE_CONHECIMENTO_DIR, "legislacao_sp")
PASTA_ITS = os.path.join(BASE_CONHECIMENTO_DIR, "its_sp")

# --- Funções de Processamento de Arquivos ---
def extrair_texto_pdf(caminho_arquivo):
    try:
        reader = PdfReader(caminho_arquivo)
        paginas = []
        for pagina in reader.pages:
            texto = pagina.extract_text()
            if texto:
                paginas.append(texto)
        return "\n".join(paginas)
    except Exception as e:
        st.error(f"Erro ao ler PDF {caminho_arquivo}: {e}")
        return ""

@st.cache_data
def carregar_base_local():
    """Carrega todo o conteúdo dos PDFs na memória para busca rápida."""
    base = []
    pastas = [
        ("legislacao_sp", PASTA_LEGISLACAO),
        ("its_sp", PASTA_ITS),
    ]

    for tipo, pasta in pastas:
        if not os.path.exists(pasta):
            st.warning(f"Pasta não encontrada: {pasta}")
            continue

        for nome_arquivo in os.listdir(pasta):
            if nome_arquivo.lower().endswith(".pdf"):
                caminho = os.path.join(pasta, nome_arquivo)
                texto = extrair_texto_pdf(caminho)
                
                base.append({
                    "tipo": tipo,
                    "arquivo": nome_arquivo,
                    "texto": texto,
                    "texto_lower": texto.lower() # Pré-processa para busca rápida
                })
    return base

# --- Funções de Busca Inteligente ---
def localizar_arquivo_especifico(pergunta):
    """Busca referências a ITs específicas (ex: IT 22, it-28) no nome do arquivo."""
    pergunta_lower = pergunta.lower()
    
    # Regex flexível para encontrar "it", "IT", "it-", "it " seguido de números
    padrao_it = re.search(r'(?:it|instru[çc][ãa]o t[ée]cnica)\s*[/\-]?\s*(\d{1,2})', pergunta_lower)
    
    if not padrao_it:
        return None

    numero_it = padrao_it.group(1).strip()
    
    base = carregar_base_local()
    for item in base:
        nome = item["arquivo"].lower()
        # Procura por "it 22 ", "it-22.", "it_22_" etc. para evitar pegar IT 220
        padrao_fiel = rf'(?:it|its_sp)\s*[/\-]?\s*0?{numero_it}\s*[._-]'
        if re.search(padrao_fiel, nome):
            return item
    return None

def buscar_na_base(pergunta, top_k=1):
    """Busca por palavras-chave dentro de toda a base de PDFs."""
    base = carregar_base_local()
    pergunta_lower = pergunta.lower().strip()
    
    palavras_ignoradas = {
        "oi", "ola", "olá", "bom", "boa", "tarde", "dia", "noite",
        "obrigado", "obrigada", "valeu", "ok", "certo", "entendi",
        "qual", "quais", "como", "onde", "quando", "sobre", "para",
        "isso", "essa", "esse", "uma", "uns", "umas", "dos", "das",
        "com", "sem", "por", "que"
    }
    
    termos = [t for t in re.findall(r"\w+", pergunta_lower) if len(t) >= 4 and t not in palavras_ignoradas]
    
    if not termos:
        return []

    resultados = []
    for item in base:
        score = 0
        arquivo_lower = item["arquivo"].lower()
        texto_lower = item["texto_lower"]
        
        for termo in termos:
            # Peso alto se a palavra estiver no nome do arquivo
            score += arquivo_lower.count(termo) * 10
            # Peso menor para ocorrências no texto
            score += texto_lower.count(termo) * 2
        
        if score >= 10:
            resultados.append({
                "score": score,
                "tipo": item["tipo"],
                "arquivo": item["arquivo"],
                "texto": item["texto"]
            })
    
    # Ordena pelo score mais alto e pega o top 1
    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:top_k]

# --- Lógica de Resposta Literal (O CORAÇÃO DO ROMANUS) ---
def responder_somente_com_base(pergunta):
    """
    Principal função: Força a IA a ler o PDF completo e extrair o parágrafo fiel,
    eliminando as respostas curtas e confusas.
    """
    st.status("Consultando base de dados...", state="running")
    
    # 1. Tenta achar arquivo específico (ex: "IT 22")
    item = localizar_arquivo_especifico(pergunta)
    
    if not item:
        # 2. Se não achar específico, busca por palavras-chave
        resultados = buscar_na_base(pergunta, top_k=1)
        if not resultados:
            st.status("Informação não encontrada.", state="error")
            return "Informação não localizada nas normas internas (ITs/Decreto 69.118/24)."
        item = resultados[0]

    st.status(f"Documento encontrado: {item['arquivo']}", state="complete")
    texto_pdf_raw = item["texto"]
    
    # 3. COMANDO DE ELITE PARA O GEMINI: Extração Literal
    # Aumentamos o contexto de 2.000 para 18.000 caracteres.
    prompt_extracao = f"""
    Como especialista técnico do CBPMESP, você deve localizar e transcrever LITERALMENTE o trecho fiel que responde: "{pergunta}".
    REGRAS OBRIGATÓRIAS:
    - Transcreva o parágrafo inteiro pertinente. Não resuma.
    - Cite o número do Item ou Artigo.
    - Não interprete, use "psis litteris" o que está escrito.
    - Responda apenas com a transcrição técnica.
    
    BASE DE TEXTO DO DOCUMENTO {item['arquivo']}:
    {texto_pdf_raw[:18000]}
    """
    
    try:
                   resposta_extracao = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt_extracao,
        )

        texto_extraido = resposta_extracao.text if resposta_extracao.text else "Sem resposta."
        return f"**Arquivo localizado:** {item['arquivo']}\n\n{texto_extraido}"

    except Exception as e:
        return f"Erro processando extração literal: {e}"

# --- Funções Auxiliares de Saudações e Internet ---
def eh_saudacao(pergunta):
    pergunta = pergunta.lower().strip()
    saudacoes = {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "obrigado", "obrigada", "valeu"}
    return pergunta in saudacoes

def responder_saudacao(pergunta):
    pergunta = pergunta.lower().strip()
    if pergunta in {"oi", "ola", "olá"}: return "Olá. Pronta para operação."
    elif pergunta == "bom dia": return "Bom dia. Pronta para operação."
    elif pergunta == "boa tarde": return "Boa tarde. Pronta para operação."
    elif pergunta == "boa noite": return "Boa noite. Pronta para operação."
    elif pergunta in {"obrigado", "obrigada", "valeu"}: return "À disposição."
    return "Pronta para operação."

def usuario_pediu_internet(pergunta):
    gatilhos = ["pesquise na internet", "use o gemini", "consultar internet", "buscar online"]
    pergunta_lower = pergunta.lower()
    return any(gatilho in pergunta_lower for gatilho in gatilhos)

# --- Definição do Prompt Base (Identidade e Regras) ---
prompt_base = """
### REGRA DE OURO (MÁXIMA PRIORIDADE) ###
1. FONTE OBRIGATÓRIA: Sua base são as ITs do CBPMESP e o Decreto 69.118/24.
2. LITERALIDADE TOTAL: Não interprete. Transcreva o texto EXATAMENTE como está na norma. Use aspas.
3. PESQUISA EXTERNA: Só use conhecimento geral/Gemini se o usuário escrever "pesquise na internet".
4. SE NÃO LOCALIZAR: Responda: "Informação não localizada nas normas internas (ITs/Decreto 69.118/24)."

Identidade:
- Seu nome é ROMANUS. IA técnica e objetiva.
- Respostas curtas, diretas e fiéis ao texto legal.

Modelo de Saída:
- NORMA: [Nome do Arquivo]
- ITEM/ARTIGO: [Número do item]
- TEXTO LITERAL: "[Texto fiel da norma]"
"""

# --- Interface Gráfica Streamlit (Estilização) ---
st.markdown("""
<style>
.topo-romanus {
    position: fixed; top: 0; left: 0; width: 100%;
    background: white; padding: 40px 0px; z-index: 9999;
    border-bottom: 1px solid #eee;
}
.topo-romanus h1 { margin: 0; font-size: 30px; font-weight: 900; color: #111; }
.bloco-chat { min-height: 75vh; display: flex; flex-direction: column; justify-content: flex-end; margin-top: 10px; }
hr { display: none !important; }
[data-testid="stHeader"] { background: white !important; box-shadow: none !important; }
.main .block-container { padding-top: 0rem !important; padding-bottom: 8rem !important; }
[data-testid="stChatInput"] textarea { font-size: 20px !important; }
[data-testid="stChatInput"] textarea::placeholder { font-size: 12px !important; }
.stChatMessage p, .stChatMessage div { font-size: 12px !important; }
</style>
<div class="topo-romanus">
    <h1>ROMANUS 5.4.1</h1>
</div>
""", unsafe_allow_html=True)

# Inicialização do Histórico
if "historico" not in st.session_state: st.session_state.historico = []

# --- Renderização do Chat ---
st.markdown('<div class="bloco-chat">', unsafe_allow_html=True)
for item in st.session_state.historico:
    role = "user" if item["tipo"] == "usuario" else "assistant"
    with st.chat_message(role):
        st.markdown(item["texto"])
st.markdown("</div>", unsafe_allow_html=True)

# Upload de Imagem (Fora da área de chat principal)
imagem = None
with st.expander("📷 Enviar imagem", expanded=False):
    uploaded_file = st.file_uploader("Escolha uma imagem", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        imagem = Image.open(uploaded_file)
        st.image(imagem, caption="Imagem enviada", use_container_width=True)

# Input de Chat
pergunta = st.chat_input("Pergunte à ROMANUS...")

# --- Processamento da Pergunta ---
if pergunta:
    pergunta = pergunta.strip()
    if pergunta:
        # Adiciona pergunta ao histórico
        st.session_state.historico.append({"tipo": "usuario", "texto": pergunta})
        with st.chat_message("user"): st.markdown(pergunta)
        
        # 1. Checa Saudações
        if eh_saudacao(pergunta):
            resposta = responder_saudacao(pergunta)
        
        # 2. Processa Imagem (Sempre via Gemini 1.5 Pro)
        elif imagem is not None:
            with st.spinner("Analisando imagem..."):
                try:
                    res_img = client.models.generate_content(
                        model="gemini-1.5-pro",
                        contents=[f"{prompt_base}\n\nAnalise tecnicamente a imagem:\n{pergunta}", imagem],
                    )
                    resposta = res_img.text if res_img.text else "Sem resposta."
                except Exception as e: resposta = f"Erro na análise de imagem: {e}"
        
        # 3. Processa Internet (Somente se solicitado explicitamente)
        elif usuario_pediu_internet(pergunta):
            with st.spinner("Consultando internet (modelo Gemini)..."):
                try:
                    res_net = client.models.generate_content(
                        model="gemini-2.0-flash", 
                        contents=f"{prompt_base}\n\nResponda usando internet:\n{pergunta}"
                    )
                    resposta = res_net.text if res_net.text else "Sem resposta."
                except Exception as e: resposta = f"Erro ao consultar Gemini: {e}"
        
        # 4. Processa Normas (O PADRÃO DO SISTEMA)
        else:
            with st.spinner("Pesquisando normas técnicas..."):
                resposta = responder_somente_com_base(pergunta)
        
        # Adiciona resposta ao histórico e renderiza
        st.session_state.historico.append({"tipo": "ia", "texto": resposta})
        with st.chat_message("assistant"): st.markdown(resposta)
        
        # Auto-scroll para o final
        st.markdown("""
        <script>
        function scrollToBottom() { window.scrollTo(0, document.body.scrollHeight); }
        window.addEventListener("load", scrollToBottom);
        setTimeout(scrollToBottom, 500);
        </script>
        """, unsafe_allow_html=True)
