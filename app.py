import streamlit as st
from google import genai
from PIL import Image
import os
import re
from pypdf import PdfReader

# =========================
# CONFIGURAÇÃO INICIAL
# =========================
st.set_page_config(page_title="ROMANUS", layout="wide")

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

BASE_CONHECIMENTO_DIR = "base_conhecimento"
PASTA_LEGISLACAO = os.path.join(BASE_CONHECIMENTO_DIR, "legislacao_sp")
PASTA_ITS = os.path.join(BASE_CONHECIMENTO_DIR, "its_sp")


# =========================
# FUNÇÕES DE BASE LOCAL
# =========================
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

    termos = [
        t for t in re.findall(r"\w+", pergunta_lower)
        if len(t) >= 3 and t not in palavras_ignoradas
    ]

    return termos


def localizar_arquivo_especifico(pergunta):
    pergunta_lower = pergunta.lower()

    padrao_it = re.search(
        r'(?:\bit\b|instru[çc][ãa]o\s+t[ée]cnica)\s*[/\-]?\s*(\d{1,2})',
        pergunta_lower
    )

    if not padrao_it:
        return None

    numero_it = padrao_it.group(1).zfill(2)
    base = carregar_base_local()

    for item in base:
        nome = item["arquivo"].lower()

        padroes_validos = [
            f"it-{numero_it}",
            f"it_{numero_it}",
            f"it {numero_it}",
            f"it-{int(numero_it)}",
            f"it_{int(numero_it)}",
            f"it {int(numero_it)}",
        ]

        if any(p in nome for p in padroes_validos):
            return item

        # tentativa extra para nomes diferentes
        if re.search(rf'\bit[\s_\-]?0?{int(numero_it)}\b', nome):
            return item

    return None


def buscar_na_base(pergunta, top_k=3):
    base = carregar_base_local()
    termos = normalizar_termos_busca(pergunta)

    if not termos:
        return []

    pergunta_lower = pergunta.lower().strip()
    resultados = []

    for item in base:
        score = 0
        arquivo_lower = item["arquivo"].lower()
        texto_lower = item["texto_lower"]

        for termo in termos:
            score += arquivo_lower.count(termo) * 10
            score += texto_lower.count(termo) * 2

        # bônus se pergunta mencionar IT e o arquivo também parecer a IT correta
        it_especifica = localizar_arquivo_especifico(pergunta)
        if it_especifica and item["arquivo"] == it_especifica["arquivo"]:
            score += 100

        # bônus pequeno se expressões compostas aparecerem
        expressoes = [
            "rota de fuga",
            "saida de emergencia",
            "saída de emergência",
            "liquido inflamavel",
            "líquido inflamável",
            "medidas de segurança",
            "controle de fumaça",
            "detecção de incêndio",
            "sistema de alarme",
        ]

        for expr in expressoes:
            if expr in pergunta_lower and expr in texto_lower:
                score += 20

        if score > 0:
            resultados.append({
                "score": score,
                "tipo": item["tipo"],
                "arquivo": item["arquivo"],
                "texto": item["texto"]
            })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:top_k]


def quebrar_em_blocos(texto):
    if not texto:
        return []

    # Primeiro tenta dividir por parágrafos maiores
    blocos = re.split(r'\n\s*\n+', texto)

    # Se vier tudo muito colado, divide também por linhas
    if len(blocos) <= 1:
        blocos = re.split(r'(?<=[\.\:\;])\s*\n', texto)

    blocos_limpos = []
    for bloco in blocos:
        bloco = bloco.strip()
        if len(bloco) >= 30:
            blocos_limpos.append(bloco)

    return blocos_limpos


def extrair_trechos_relevantes(texto, pergunta, limite=3):
    termos = normalizar_termos_busca(pergunta)
    if not texto.strip():
        return []

    blocos = quebrar_em_blocos(texto)
    if not blocos:
        return []

    melhores = []

    for bloco in blocos:
        bloco_lower = bloco.lower()
        score = 0

        for termo in termos:
            score += bloco_lower.count(termo) * 3

        # bônus para blocos com marcação de item, artigo, seção
        if re.search(r'\b(item|art\.?|artigo|seção|secao|capítulo|capitulo)\b', bloco_lower):
            score += 3

        if score > 0:
            melhores.append((score, bloco))

    melhores.sort(key=lambda x: x[0], reverse=True)

    trechos = []
    vistos = set()

    for score, bloco in melhores:
        chave = bloco[:200]
        if chave not in vistos:
            vistos.add(chave)
            trechos.append(bloco)
        if len(trechos) >= limite:
            break

    return trechos


def montar_contexto_base(pergunta):
    resultados = buscar_na_base(pergunta, top_k=3)

    if not resultados:
        return ""

    blocos_contexto = []

    for item in resultados:
        trechos = extrair_trechos_relevantes(item["texto"], pergunta, limite=2)

        if not trechos:
            trecho = item["texto"][:1500].strip()
        else:
            trecho = "\n\n".join(trechos)

        blocos_contexto.append(
            f"ARQUIVO: {item['arquivo']}\n"
            f"SCORE: {item['score']}\n"
            f"TRECHOS DA BASE:\n{trecho}"
        )

    return "\n\n---\n\n".join(blocos_contexto)

def pergunta_pede_so_localizacao(pergunta):
    p = pergunta.lower().strip()

    gatilhos = [
        "qual it fala sobre",
        "qual it trata de",
        "qual norma fala sobre",
        "qual norma trata de",
        "qual instrução técnica fala sobre",
        "qual instrução técnica trata de",
        "em qual it está",
        "em qual norma está",
        "qual arquivo fala sobre",
        "qual arquivo trata de",
    ]

    return any(g in p for g in gatilhos)
def responder_somente_com_base(pergunta):
    item_especifico = localizar_arquivo_especifico(pergunta)

    if item_especifico:
        item = item_especifico
    else:
        resultados = buscar_na_base(pergunta, top_k=3)
        if not resultados:
            return "Informação não localizada nas normas internas (ITs/Decreto 69.118/24)."
        item = resultados[0]

    texto = item["texto"] if item["texto"] else ""
    if not texto.strip():
        return f"Localizei o arquivo {item['arquivo']}, mas não consegui extrair texto útil do PDF."

    # Se a pergunta for só para identificar qual norma trata do assunto,
    # responde apenas com o nome do arquivo.
    if pergunta_pede_so_localizacao(pergunta):
        return f"**Arquivo localizado:** {item['arquivo']}"

    trechos = extrair_trechos_relevantes(texto, pergunta, limite=2)

    if not trechos:
        trecho_literal = texto[:800].strip()
        return (
            f"**Arquivo localizado:** {item['arquivo']}\n\n"
            f"**Trecho literal da base:**\n\n"
            f"\"{trecho_literal}\""
        )

    trecho_literal = "\n\n".join([f"\"{t}\"" for t in trechos])

    return (
        f"**Arquivo localizado:** {item['arquivo']}\n\n"
        f"**Trecho literal da base:**\n\n"
        f"{trecho_literal}"
    )

# =========================
# FUNÇÕES AUXILIARES
# =========================
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


def usuario_pediu_gemini(pergunta):
    gatilhos = [
        "use o gemini",
        "consultar gemini",
        "pesquise na internet",
        "pesquisar na internet",
        "busque na internet",
        "buscar na internet",
        "complemente",
        "complementar com internet",
        "resposta com internet",
    ]
    pergunta_lower = pergunta.lower()
    return any(gatilho in pergunta_lower for gatilho in gatilhos)


def pergunta_eh_normativa(pergunta):
    p = pergunta.lower().strip()

    gatilhos = [
        "it ", "it-", "instrução técnica", "instrucao tecnica",
        "lei", "decreto", "artigo", "art.", "item", "inciso",
        "norma", "regulamento", "avcb", "clcb", "cbpmesp",
        "bombeiro", "extintor", "hidrante", "mangotinho",
        "rota de fuga", "saída de emergência", "saida de emergencia",
        "detecção", "deteccao", "alarme", "sprinkler",
        "líquido inflamável", "liquido inflamavel",
        "combustível", "combustivel",
        "medidas de segurança", "ocupação", "ocupacao",
        "carga de incêndio", "carga de incendio"
    ]

    return any(g in p for g in gatilhos)


# =========================
# PROMPT BASE DO GEMINI
# =========================
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

Estilo:
- Frases curtas.
- Linguagem profissional.

Postura de comunicação:
- Seja sempre educada, respeitosa e profissional.
- Trate o usuário com cordialidade natural, sem excesso de formalismo e sem bajulação.
- Responda com gentileza, clareza e objetividade.
- Evite respostas secas, ásperas ou ríspidas.
- Mesmo quando corrigir o usuário ou discordar, faça isso com respeito.
- Demonstre disposição para ajudar, sem parecer servil.
- Quando não souber algo, diga com honestidade e educação.
- Nunca invente artigo, inciso, item, número de norma ou entendimento.

Fundamentação jurídica e normativa:
- Sempre que a pergunta envolver tema jurídico, administrativo, técnico-normativo ou regulatório, responda com base em lei, decreto, norma, instrução técnica, regulamento ou ato oficial aplicável.
- Sempre que possível, cite expressamente a base utilizada, com número da norma, ano e artigo, item ou dispositivo relevante.
- Em temas de segurança contra incêndio no Estado de São Paulo, priorize a legislação paulista e as Instruções Técnicas do Corpo de Bombeiros do Estado de São Paulo.
- Diferencie exigência legal, exigência regulamentar, exigência técnica e recomendação prática.
- Se não tiver segurança quanto ao fundamento exato, diga isso claramente.

Modelo de saída preferencial:
- Resposta objetiva: [resposta direta]
- Fundamento: [norma, artigo, item ou dispositivo]
- Conclusão prática: [o que isso significa na prática]
"""


# =========================
# FUNÇÃO PRINCIPAL DE RESPOSTA
# =========================
def gerar_resposta(pergunta: str, imagem=None) -> str:
    pergunta = pergunta.strip()

    if not pergunta:
        return "Escreva uma pergunta."

    if eh_saudacao(pergunta):
        return responder_saudacao(pergunta)

    # IMAGEM -> GEMINI
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

    # PERGUNTA NORMATIVA -> BASE LOCAL PRIMEIRO
    if pergunta_eh_normativa(pergunta):
        resultados_base = buscar_na_base(pergunta, top_k=3)

        # Se achou base, responde literal da base
        if resultados_base or localizar_arquivo_especifico(pergunta):
            # Só usa Gemini se o usuário pedir explicitamente complemento/internet
            if usuario_pediu_gemini(pergunta):
                contexto_base = montar_contexto_base(pergunta)

                pergunta_final = f"""
{prompt_base}

Use a base interna abaixo como prioridade.
Só complemente com conhecimento geral porque o usuário pediu isso explicitamente.
Não invente norma, artigo, item ou fundamento.

BASE INTERNA:
{contexto_base}

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

            return responder_somente_com_base(pergunta)

        # Se não achou base e o usuário pediu internet/Gemini
        if usuario_pediu_gemini(pergunta):
            pergunta_final = f"""
{prompt_base}

O usuário pediu uso do Gemini/internet explicitamente.
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

        return "Informação não localizada nas normas internas (ITs/Decreto 69.118/24)."

    # PERGUNTA GERAL -> GEMINI
    try:
        resposta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{prompt_base}\n\nPERGUNTA DO USUÁRIO:\n{pergunta}",
        )
        texto = getattr(resposta, "text", None)
        return texto.strip() if texto and texto.strip() else "Sem resposta no momento."
    except Exception as e:
        return f"Erro ao consultar o Gemini: {e}"


# =========================
# CSS / INTERFACE
# =========================
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


# =========================
# SESSION STATE
# =========================
if "historico" not in st.session_state:
    st.session_state.historico = []

if "imagem_upload" not in st.session_state:
    st.session_state.imagem_upload = None


# =========================
# RENDERIZAÇÃO DO CHAT
# =========================
st.markdown('<div class="bloco-chat">', unsafe_allow_html=True)

for item in st.session_state.historico:
    role = "user" if item["tipo"] == "usuario" else "assistant"
    with st.chat_message(role):
        st.markdown(item["texto"])

st.markdown("</div>", unsafe_allow_html=True)


# =========================
# UPLOAD DE IMAGEM
# =========================
with st.expander("📷 Enviar imagem", expanded=False):
    uploaded_file = st.file_uploader(
        "Escolha uma imagem",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file is not None:
        st.session_state.imagem_upload = Image.open(uploaded_file)
        st.image(st.session_state.imagem_upload, caption="Imagem enviada", use_container_width=True)

imagem = st.session_state.imagem_upload


# =========================
# INPUT DO CHAT
# =========================
pergunta = st.chat_input("Pergunte à ROMANUS...")

if pergunta:
    pergunta = pergunta.strip()

    if pergunta:
        st.session_state.historico.append({"tipo": "usuario", "texto": pergunta})

        with st.chat_message("user"):
            st.markdown(pergunta)

        with st.spinner("Processando..."):
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
