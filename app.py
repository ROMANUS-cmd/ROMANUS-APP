import streamlit as st
from google import genai

st.set_page_config(page_title="ROMANUS 5.4.1", layout="wide")

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.title("ROMANUS")
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

    resposta = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{prompt_base}\n\nPergunta do usuário: {pergunta}",
    )

    texto_resposta = resposta.text.strip() if resposta.text else "Sem resposta no momento."

    st.session_state.historico.append({"tipo": "ia", "texto": texto_resposta})
    st.session_state.caixa_texto = ""

st.text_input("Digite sua ordem:", key="caixa_texto")
st.button("Enviar", on_click=enviar_pergunta)

for item in st.session_state.historico:
    if item["tipo"] == "usuario":
        st.markdown(f"*Você:* {item['texto']}")
    else:
        st.markdown(f"*ROMANUS:* {item['texto']}")
