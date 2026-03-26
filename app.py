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

def responder_somente_com_base(pergunta):
    resultados = buscar_na_base(pergunta, top_k=3)

    if not resultados:
        return "Não localizei base suficiente nos arquivos internos da ROMANUS para responder com segurança."

    item = resultados[0]
    texto = item["texto"] if item["texto"] else ""

    termos = [t for t in re.findall(r"\w+", pergunta.lower()) if len(t) >= 4]

    trechos = re.split(r'(?<=[\.\n])', texto)
    melhores_trechos = []

    for trecho in trechos:
        score = 0
        trecho_lower = trecho.lower()
        for termo in termos:
            score += trecho_lower.count(termo)
        if score > 0:
            melhores_trechos.append((score, trecho.strip()))

    melhores_trechos.sort(key=lambda x: x[0], reverse=True)
    trechos_escolhidos = [t[1] for t in melhores_trechos[:2] if t[1]]

    fundamento = " ".join(trechos_escolhidos).strip()

    if not fundamento:
        fundamento = texto[:800].strip()

    resposta = (
        f"Resposta objetiva: com base no arquivo {item['arquivo']}, este é o fundamento mais relevante para a pergunta.\n"
        f"Fundamento localizado: {fundamento}\n"
        f"Base consultada: {item['arquivo']}\n"
        f"Conclusão prática: resposta extraída diretamente da base interna da ROMANUS."
    )

    linhas = [linha.strip() for linha in resposta.splitlines() if linha.strip()]
    return "\n".join(linhas[:12])

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
    padding-bottom: 4rem !important;
}

[data-testid="stChatInput"] textarea {
    font-size: 22px !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    font-size: 22px !important;
}

.stChatMessage p,
.stChatMessage div {
    font-size: 28px !important;
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
- Prefira frases como:
  "Claro."
  "Entendido."
  "Certo."
  "Vou direto ao ponto."
  "Segue a resposta objetiva."
  "Posso organizar isso para você."
- Quando não souber algo, diga com honestidade e educação, como:
  "Não tenho segurança para afirmar isso."
  "Preciso de mais dados para responder com precisão."
  "Não localizei base suficiente para confirmar isso."
- Quando o usuário agradecer, responda com educação, como:
  "De nada."
  "À disposição."
  "Sempre que precisar."
  "Fico à disposição."
- Mantenha tom firme, técnico e objetivo, mas sempre humano e cortês.
- Nunca use ironia ofensiva, arrogância ou impaciência.
- Nunca humilhe o usuário, mesmo que a pergunta seja simples, repetida ou confusa.
- Se a pergunta estiver ambígua, peça esclarecimento com educação.
- Priorize sempre uma comunicação útil, respeitosa e confiável.
- Priorize sempre uma comunicação útil, respeitosa e confiável.

Fundamentação jurídica e normativa:
- Sempre que a pergunta envolver tema jurídico, administrativo, técnico-normativo ou regulatório, responda com base em lei, decreto, norma, instrução técnica, regulamento ou ato oficial aplicável.
- Sempre que possível, cite expressamente a base utilizada, com número da norma, ano e artigo, item ou dispositivo relevante.
- Quando houver hierarquia normativa, priorize nesta ordem:
  1. Constituição
  2. Lei complementar
  3. Lei ordinária
  4. Decreto
  5. Regulamento
  6. Instrução técnica
  7. Norma complementar aplicável
- Nunca invente artigo, inciso, item, número de norma ou entendimento.
- Se não tiver segurança quanto ao fundamento exato, diga isso de forma clara e respeitosa.
- Quando a pergunta depender de norma estadual ou local, priorize a norma do ente competente.
- Em temas de segurança contra incêndio no Estado de São Paulo, priorize a legislação paulista e as Instruções Técnicas do Corpo de Bombeiros do Estado de São Paulo.
- Em respostas técnicas, diferencie com clareza:
  - o que é exigência legal;
  - o que é exigência regulamentar;
  - o que é exigência técnica;
  - o que é recomendação prática.
- Quando houver risco de interpretação controvertida, informe que a conclusão depende da análise do caso concreto e da norma aplicável.
- Sempre que possível, estruture a resposta assim:
  1. resposta objetiva;
  2. fundamento legal ou normativo;
  3. conclusão prática.
- Se o usuário pedir resposta curta, mantenha a fundamentação enxuta, mas ainda cite a base principal.
- Se o usuário pedir resposta completa, detalhe a norma, a lógica da aplicação e a consequência prática.

Modelo de saída preferencial:
- Resposta objetiva: [resposta direta]
- Fundamento: [norma, artigo, item ou dispositivo]
- Conclusão prática: [o que isso significa na prática]
"""

if "historico" not in st.session_state:
    st.session_state.historico = []

if "pergunta" not in st.session_state:
    st.session_state.pergunta = ""

def gerar_resposta(pergunta: str, imagem=None) -> str:
    pergunta = pergunta.strip()

    if not pergunta:
        return "Escreva uma pergunta."

    resultados_base = buscar_na_base(pergunta, top_k=3)
    pediu_gemini = usuario_pediu_gemini(pergunta)

    # Se houver imagem, ainda precisa do Gemini
    if imagem is not None:
        pediu_gemini = True

    # Regra principal:
    # Se achou base suficiente e o usuário NÃO pediu Gemini, responde só com a base
    if resultados_base and not pediu_gemini:
        return responder_somente_com_base(pergunta)

    # Se não achou base suficiente e o usuário também não pediu Gemini
    if not resultados_base and not pediu_gemini:
        return (
            "Não localizei base suficiente nos arquivos internos da ROMANUS. "
            "Se quiser, peça explicitamente para usar o Gemini ou pesquisar na internet."
        )

    # Só chega aqui se o usuário pediu Gemini explicitamente
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
        if imagem is not None:
            resposta = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[pergunta_final, imagem],
            )
        else:
            resposta = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=pergunta_final,
            )

        texto = getattr(resposta, "text", None)
        if texto and texto.strip():
            return texto.strip()

        return "Sem resposta no momento."
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
