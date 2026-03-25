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
    def montar_contexto_base(pergunta):
    resultados = buscar_na_base(pergunta, top_k=3)

    if not resultados:
        return ""

    partes = []
    for item in resultados:
        trecho = item["texto"][:4000] if item["texto"] else ""
        partes.append(
            f"ARQUIVO: {item['arquivo']}\n"
            f"TIPO: {item['tipo']}\n"
            f"TRECHO:\n{trecho}\n"
        )

    return "\n\n".join(partes)
    base = carregar_base_local()
    pergunta_lower = pergunta.lower()
    termos = re.findall(r"\w+", pergunta_lower)

    resultados = []

    for item in base:
        score = 0

        for termo in termos:
            if len(termo) < 3:
                continue

            score += item["arquivo"].lower().count(termo) * 5
            score += item["texto_lower"].count(termo)

        if score > 0:
            resultados.append({
                "score": score,
                "tipo": item["tipo"],
                "arquivo": item["arquivo"],
                "texto": item["texto"]
            })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:top_k]

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

    if "internet" in pergunta.lower() or "pesquisa" in pergunta.lower():
        return "Sim. Respondo com base em critérios técnicos, hierarquia normativa e confirmação complementar por fontes confiáveis da internet."

    try:
        if imagem is not None:
            resposta = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[f"{prompt_base}\n\nPergunta do usuário: {pergunta}", imagem],
            )
        else:
            resposta = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{prompt_base}\n\nPergunta do usuário: {pergunta}",
            )

        texto = getattr(resposta, "text", None)
        if texto and texto.strip():
            return texto.strip()

        return "Sem resposta no momento."
    except Exception:
        return "Erro ao consultar o modelo. Verifique a chave da API, os logs e tente novamente."


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
