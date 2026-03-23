import streamlit as st
from google import genai

st.set_page_config(page_title="ROMANUS", layout="wide")

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.markdown("""
<style>
.topo-romanus {
    background: white;
    padding: 0 10px 0 10px;
   margin: -70px 0 0 0;
}

.topo-romanus h1 {
    margin: 0;
    font-size: 30px;
    font-weight: 900;
    line-height: 1;
    color: #111111;
    letter-spacing: 1px;
}

.bloco-chat {
    margin-top: 8px;
}

hr {
    display: none !important;
}

[data-testid="stHeader"] {
    background: white !important;
    border-bottom: none !important;
    box-shadow: none !important;
}

.main .block-container {
    padding-top: 0rem !important;
    padding-bottom: 2rem !important;
}
    padding-top: 0.6rem !important;
    padding-bottom: 2rem !important;
}
    padding-top: 6.2rem !important;
    padding-bottom: 2rem !important;
}
</style>

<div class="topo-romanus">
    <h1>ROMANUS</h1>
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
- Quando perguntarem "quem te criou?", responda: "Fui criada por um grupo de especialistas em inteligência artificial reunidos sob o nome ROMANUS.IA."
- Só mencione Google, Gemini, modelo, infraestrutura ou base técnica se o usuário perguntar explicitamente sobre isso.
- Evite frases vagas e genéricas.
- Priorize clareza, firmeza e utilidade prática.

Estilo:
- Frases curtas.
- Linguagem profissional.
- Sem bajulação.
- Sem conversa fiada.
"""

if "historico" not in st.session_state:
    st.session_state.historico = []

if "pergunta" not in st.session_state:
    st.session_state.pergunta = ""


def gerar_resposta(pergunta: str) -> str:
    pergunta = pergunta.strip()

    if not pergunta:
        return "Escreva uma pergunta."

    if "internet" in pergunta.lower() or "pesquisa" in pergunta.lower():
        return "Sim. Respondo com base em critérios técnicos, hierarquia normativa e confirmação complementar por fontes confiáveis da internet."

    try:
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

pergunta = st.chat_input("Pergunte à ROMANUS...")

if pergunta:
    pergunta = pergunta.strip()

    if pergunta:
        st.session_state.historico.append({"tipo": "usuario", "texto": pergunta})

        with st.chat_message("user"):
            st.markdown(pergunta)

        texto_resposta = gerar_resposta(pergunta)

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
