import streamlit as st
from google import genai
from PIL import Image
import os
import re
from pypdf import PdfReader

st.set_page_config(page_title="ROMANUS", layout="wide")

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)
BASE_CONHECIMENTO_DIR = "base_conhecimento"
PASTA_LEGISLACAO = os.path.join(BASE_CONHECIMENTO_DIR, "legislacao_sp")
PASTA_ITS = os.path.join(BASE_CONHECIMENTO_DIR, "its_sp")


def extrair_texto_pdf(caminho_arquivo):
    try:
        reader = PdfReader(caminho_arquivo)
        paginas = []
        for pagina in reader.pages:
            texto = pagina.extract_text()
            if texto:
                paginas.append(texto)
        return "\n".join(paginas)
    except Exception:
        return ""


@st.cache_data
def carregar_base_local():
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

                base.append({
                    "tipo": tipo,
                    "arquivo": nome_arquivo,
                    "caminho": caminho,
                    "texto": texto,
                    "texto_lower": texto.lower()
                })

    return base

def buscar_na_base(pergunta, top_k=3):
    base = carregar_base_local()
    pergunta_lower = pergunta.lower().strip()

    palavras_ignoradas = {
        "oi", "ola", "olá", "bom", "boa", "tarde", "dia", "noite",
        "obrigado", "obrigada", "valeu", "ok", "certo", "entendi",
        "qual", "quais", "como", "onde", "quando", "sobre", "para",
        "isso", "essa", "esse", "uma", "uns", "umas", "dos", "das",
        "com", "sem", "por", "que"
    }

    termos = [
        t for t in re.findall(r"\w+", pergunta_lower)
        if len(t) >= 4 and t not in palavras_ignoradas
    ]

    if not termos:
        return []

    resultados = []

    for item in base:
        score = 0
        arquivo_lower = item["arquivo"].lower()
        texto_lower = item["texto_lower"]

        for termo in termos:
            score += arquivo_lower.count(termo) * 8
            score += texto_lower.count(termo) * 2

        if score >= 10:
            resultados.append({
                "score": score,
                "tipo": item["tipo"],
                "arquivo": item["arquivo"],
                "texto": item["texto"]
            })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:top_k]
def eh_saudacao(pergunta):
    pergunta = pergunta.lower().strip()
    saudacoes = {
        "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite",
        "obrigado", "obrigada", "valeu"
    }
    return pergunta in saudacoes


def responder_saudacao(pergunta):
    pergunta = pergunta.lower().strip()

    if pergunta in {"oi", "ola", "olá"}:
        return "Olá. Pronta para operação."
    elif pergunta == "bom dia":
        return "Bom dia. Pronta para operação."
    elif pergunta == "boa tarde":
        return "Boa tarde. Pronta para operação."
    elif pergunta == "boa noite":
        return "Boa noite. Pronta para operação."
    elif pergunta in {"obrigado", "obrigada", "valeu"}:
        return "À disposição."

    return "Pronta para operação."


def montar_contexto_base(pergunta):
    resultados = buscar_na_base(pergunta, top_k=3)

    if not resultados:
        return ""

    blocos = []
    for item in resultados:
        texto = item["texto"][:2000].strip()
        blocos.append(
            f"ARQUIVO: {item['arquivo']}\n"
            f"SCORE: {item['score']}\n"
            f"TRECHO:\n{texto}"
        )

    return "\n\n---\n\n".join(blocos)
def usuario_pediu_gemini(pergunta):
    gatilhos = [
        "use o gemini",
        "consultar gemini",
        "pesquise na internet",
        "pesquisar na internet",
        "busque na internet",
        "complemente",
        "complementar com internet",
        "resposta com internet",
    ]
    pergunta_lower = pergunta.lower()
    return any(gatilho in pergunta_lower for gatilho in gatilhos)

def localizar_arquivo_especifico(pergunta):
    pergunta_lower = pergunta.lower()

    padrao_it = re.search(r'it\s*(\d{1,2})\s*[/\-]?\s*(\d{2,4})?', pergunta_lower)
    if not padrao_it:
        padrao_it = re.search(r'instrução técnica\s*(\d{1,2})\s*[/\-]?\s*(\d{2,4})?', pergunta_lower)

    if not padrao_it:
        padrao_it = re.search(r'instrucao tecnica\s*(\d{1,2})\s*[/\-]?\s*(\d{2,4})?', pergunta_lower)

    if not padrao_it:
        return None

    numero_it = padrao_it.group(1)

    base = carregar_base_local()
    for item in base:
        nome = item["arquivo"].lower()
        if f"it {numero_it}" in nome or f"it_{numero_it}" in nome or f"it-{numero_it}" in nome or f"{numero_it}-" in nome:
            return item

    return None
def responder_somente_com_base(pergunta):
    item_especifico = localizar_arquivo_especifico(pergunta)
    
    if item_especifico:
        item = item_especifico
    else:
        resultados = buscar_na_base(pergunta, top_k=1)
        if not resultados:
            return "Não localizei base interna suficiente para responder com segurança."
        item = resultados[0]

    texto_pdf = item["texto"]
    
    # Comando para o modelo extrair o texto fiel do banco de dados
    prompt_extracao = f"""
    Baseado no documento {item['arquivo']}, localize e transcreva LITERALMENTE o trecho que responde à pergunta: "{pergunta}".
    REGRAS:
    - Cite o número do Item ou Artigo.
    - Transcreva o parágrafo inteiro pertinente sem alterações.
    
    TEXTO PARA PESQUISA:
    {texto_pdf[:18000]}
    """
    
    try:
        # Aqui o modelo 2.0-flash processa a extração literal
        resposta_extracao = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt_extracao,
        )
        return f"**Arquivo localizado:** {item['arquivo']}\n\n{resposta_extracao.text}"
    except Exception as e:
        return f"Erro na extração literal: {e}"

    )
st.markdown("""
<style>
.topo-romanus {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    background: white;
    padding: 40px 0px;
    z-index: 9999;
    border-bottom: 1px solid #eee;
}

.topo-romanus h1 {
    margin: 0;
    font-size: 30px;
    font-weight: 900;
    color: #111;
}

.bloco-chat {
    min-height: 75vh;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    margin-top: 10px;
}

hr {
    display: none !important;
}

[data-testid="stHeader"] {
    background: white !important;
    box-shadow: none !important;
}

.main .block-container {
    padding-top: 0rem !important;
    padding-bottom: 8rem !important;
}

[data-testid="stChatInput"] textarea {
    font-size: 20px !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    font-size: 12px !important;
}

.stChatMessage p,
.stChatMessage div {
    font-size: 12px !important;
}
</style>

<div class="topo-romanus">
    <h1>ROMANUS 5.4.1</h1>
</div>
""", unsafe_allow_html=True)
prompt_base = """
Você é ROMANUS, uma IA de respostas diretas, técnicas e objetivas.

Identidade:
- Seu nome é ROMANUS.
- Você responde sempre em português do Brasil.
- Você é direta, técnica, objetiva e útil.
- Você não enrola, não floreia e não usa resposta genérica.

Comportamento:
- Quando perguntarem "quem é você?", responda: "Sou ROMANUS, uma IA de respostas diretas, técnicas e objetivas."
- Quando perguntarem "quem te criou?", responda: "Fui criada por um grupo de especialistas em inteligência artificial reunidos sob o nome ROMANUS.IA, o idealizador é o engenheiro André L. R. Lopes."
- Só mencione Google, Gemini, modelo, infraestrutura ou base técnica se o usuário perguntar explicitamente sobre isso.
- Evite frases vagas e genéricas.
- Priorize clareza, firmeza e utilidade prática.

### REGRA DE OURO (MÁXIMA PRIORIDADE) ###
1. FONTE OBRIGATÓRIA: Sua base são as ITs do CBPMESP e o Decreto 69.118/24.
2. LITERALIDADE TOTAL: Não interprete. Transcreva o texto EXATAMENTE como está na norma. Use aspas.
3. PESQUISA EXTERNA: Só use conhecimento geral/Gemini se o usuário escrever "pesquise na internet".
4. SE NÃO LOCALIZAR: Responda: "Informação não localizada nas normas internas (ITs/Decreto 69.118/24)."

Modelo de Saída:
- NORMA: [Nome do Arquivo]
- ITEM/ARTIGO: [Número do item]
- TEXTO LITERAL: "[Texto fiel da norma]"
"""

if "historico" not in st.session_state:
    st.session_state.historico = []

if "pergunta" not in st.session_state:
    st.session_state.pergunta = ""

def pergunta_eh_normativa(pergunta):
    p = pergunta.lower().strip()

    gatilhos = [
        "it ", "it-", "instrução técnica", "instrucao tecnica",
        "lei", "decreto", "artigo", "art.", "item", "inciso",
        "norma", "regulamento", "avcb", "clcb", "cbpmesp",
        "bombeiro", "extintor", "hidrante", "mangotinho",
        "rota de fuga", "saída de emergência", "saida de emergencia",
        "detecção", "deteccao", "alarme", "sprinkler",
        "líquido inflamável", "liquido inflamavel", "combustível", "combustivel"
    ]

    return any(g in p for g in gatilhos)
def gerar_resposta(pergunta: str, imagem=None) -> str:
    pergunta = pergunta.strip()

    if not pergunta:
        return "Escreva uma pergunta."

    if eh_saudacao(pergunta):
        return responder_saudacao(pergunta)

    # Imagem sempre vai para o Gemini
    if imagem is not None:
        try:
            resposta = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[f"{prompt_base}\n\nPERGUNTA DO USUÁRIO:\n{pergunta}", imagem],
            )
            texto = getattr(resposta, "text", None)
            return texto.strip() if texto and texto.strip() else "Sem resposta no momento."
        except Exception as e:
            return f"Erro ao consultar o Gemini: {e}"

    # Pergunta normativa/técnica = base local primeiro
    if pergunta_eh_normativa(pergunta):
        resultados_base = buscar_na_base(pergunta, top_k=3)

        if resultados_base:
            return responder_somente_com_base(pergunta)

        if usuario_pediu_gemini(pergunta):
            contexto_base = montar_contexto_base(pergunta)

            if contexto_base:
                pergunta_final = f"""
{prompt_base}

Use a base interna da ROMANUS abaixo como prioridade.
Só complemente com conhecimento geral porque o usuário pediu isso explicitamente.

BASE INTERNA ENCONTRADA:
{contexto_base}

PERGUNTA DO USUÁRIO:
{pergunta}
"""
            else:
                pergunta_final = f"""
{prompt_base}

O usuário pediu uso do Gemini/Internet explicitamente.
Não foi localizada base interna suficiente.
Não invente norma, artigo, item ou fundamento.

PERGUNTA DO USUÁRIO:
{pergunta}
"""

            try:
                resposta = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=pergunta_final,
                )
                texto = getattr(resposta, "text", None)
                return texto.strip() if texto and texto.strip() else "Sem resposta no momento."
            except Exception as e:
                return f"Erro ao consultar o Gemini: {e}"

        return "Não localizei base interna suficiente para responder com segurança."

    # Pergunta geral = Gemini direto
    try:
        resposta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{prompt_base}\n\nPERGUNTA DO USUÁRIO:\n{pergunta}",
        )
        texto = getattr(resposta, "text", None)
        return texto.strip() if texto and texto.strip() else "Sem resposta no momento."
    except Exception as e:
        return f"Erro ao consultar o Gemini: {e}"
st.markdown('<div class="bloco-chat">', unsafe_allow_html=True)

for item in st.session_state.historico:
    role = "user" if item["tipo"] == "usuario" else "assistant"
    with st.chat_message(role):
        st.markdown(item["texto"])

st.markdown("</div>", unsafe_allow_html=True)
imagem = None

with st.expander("📷 Enviar imagem", expanded=False):
    uploaded_file = st.file_uploader(
        "Escolha uma imagem",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file is not None:
        imagem = Image.open(uploaded_file)
        st.image(imagem, caption="Imagem enviada", use_container_width=True)

pergunta = st.chat_input("Pergunte à ROMANUS...")

if pergunta:
    pergunta = pergunta.strip()

    if pergunta:
        st.session_state.historico.append({"tipo": "usuario", "texto": pergunta})

        with st.chat_message("user"):
            st.markdown(pergunta)

        texto_resposta = gerar_resposta(pergunta, imagem)

        st.session_state.historico.append({"tipo": "ia", "texto": texto_resposta})

        with st.chat_message("assistant"):
            st.markdown(texto_resposta)

        st.markdown("""
        <script>
        function scrollToBottom() {
            window.scrollTo(0, document.body.scrollHeight);
        }

        window.addEventListener("load", scrollToBottom);
        setTimeout(scrollToBottom, 200);
        setTimeout(scrollToBottom, 600);
        setTimeout(scrollToBottom, 1000);
        </script>
        """, unsafe_allow_html=True)
