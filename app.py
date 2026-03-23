import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="ROMANUS 5.4.1", layout="wide")

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.markdown("""
<style>
.titulo-topo {
    font-size: 56px;
    font-weight: 800;
    margin-bottom: 0;
    line-height: 1.1;
}
.versao-topo {
    font-size: 32px;
    font-weight: 600;
    color: #6b7280;
    margin-left: 6px;
    vertical-align: middle;
}
</style>

<div class="titulo-topo">
    ROMANUS<span class="versao-topo">5.4.1</span>
</div>
""", unsafe_allow_html=True)
st.subheader("A IA que não passa pano.")

prompt_base = """
Você é ROMANUS, a IA que não passa pano.

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

if "caixa_texto" not in st.session_state:
    st.session_state.caixa_texto = ""

def enviar_pergunta():
    pergunta = st.session_state.caixa_texto.strip()

    if not pergunta:
        return

    st.session_state.historico.append({"tipo": "usuario", "texto": pergunta})

for item in st.session_state.historico:
    role = "user" if item["tipo"] == "usuario" else "assistant"
    with st.chat_message(role):
        st.markdown(item["texto"])

pergunta = st.chat_input("Pergunte à ROMANUS...")

if pergunta:
    st.session_state.historico.append({"tipo": "usuario", "texto": pergunta})

with st.chat_message("user"):
    st.markdown(pergunta)

if "internet" in pergunta.lower() or "pesquisa" in pergunta.lower():
    texto_resposta = "Sim. Respondo com base em critérios técnicos, hierarquia normativa e confirmação complementar por fontes confiáveis da internet."
else:
    resposta = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{prompt_base}\n\nPergunta do usuário: {pergunta}",
    )

    texto_resposta = resposta.text.strip() if resposta.text else "Sem resposta no momento."

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
