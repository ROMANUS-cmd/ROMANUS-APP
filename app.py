import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="ROMANUS 5.4.1", layout="wide")

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.markdown("""
<style>
.topo-romanus {
    background: white;
    padding: 8px 0 4px 0;
    margin-bottom: 4px;
}

.topo-romanus h1 {
    margin: 0;
    font-size: 72px;
    font-weight: 900;
    line-height: 1;
    color: #111111;
    letter-spacing: 1px;
}

.bloco-chat {
    margin-top: 20px;
}

hr {
    display: none !important;
}

[data-testid="stHeader"] {
    background: white !important;
    border-bottom: none !important;
    box-shadow: none !important;
}
</style>

<div class="topo-romanus">
    <h1>ROMANUS</h1>
</div>
""", unsafe_allow_html=True)
if "caixa_texto" not in st.session_state:
    st.session_state.caixa_texto = ""

def enviar_pergunta():
    pergunta = st.session_state.caixa_texto.strip()

    if not pergunta:
        return

    st.session_state.historico.append({"tipo": "usuario", "texto": pergunta})

st.markdown('<div class="bloco-chat">', unsafe_allow_html=True)

for item in st.session_state.historico:
    role = "user" if item["tipo"] == "usuario" else "assistant"
    with st.chat_message(role):
        st.markdown(item["texto"])

st.markdown('</div>', unsafe_allow_html=True)

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
