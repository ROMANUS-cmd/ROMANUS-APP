import streamlit as st
from google import genai

st.set_page_config(
    page_title="ROMANUS",
    page_icon="capa_romanus.png.PNG",
    layout="wide"
)

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.markdown("""
<style>
/* Cabeçalho fixo */
.topo-romanus {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 9999;
    background: white;
    width: 100%;
    padding: 10px 16px 6px 16px;
    border-bottom: 1px solid #f0f0f0;
}

.topo-romanus h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 900;
    line-height: 1;
    color: #111111;
    letter-spacing: 1px;
}

.topo-romanus p {
    margin: 6px 0 0 0;
    font-size: 14px;
    color: #444444;
}

/* Esconde linha padrão */
hr {
    display: none !important;
}

/* Remove cabeçalho padrão do Streamlit */
[data-testid="stHeader"] {
    background: white !important;
    border-bottom: none !important;
    box-shadow: none !important;
}

/* Dá espaço para o topo fixo e para a barra de digitação */
.main .block-container {
    padding-top: 5.5rem !important;
    padding-bottom: 7rem !important;
}

/* Melhora visual no celular */
[data-testid="stChatMessage"] {
    margin-bottom: 0.4rem;
}
</style>

<div class="topo-romanus">
    <h1>ROMANUS</h1>
    <p>Sou ROMANUS, uma IA de respostas diretas, técnicas e objetivas.</p>
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
- No máximo 10 linhas, exceto se o usuário solicitar resposta mais completa.
- Linguagem profissional.
- Educação sem bajulação excessiva.
- Objetividade sem grosseria.
- Cordialidade natural quando o contexto pedir.
- Quando o usuário agradecer, responda de forma educada, como:
  "De nada."
  "À disposição."
  "Por nada."
  "Sempre que precisar."
"""

if "historico" not in st.session_state:
    st.session_state.historico = []

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

# Exibe histórico
for item in st.session_state.historico:
    role = "user" if item["tipo"] == "usuario" else "assistant"
    with st.chat_message(role):
        st.markdown(item["texto"])

# Campo de entrada
pergunta = st.chat_input("Pergunte à ROMANUS...")

if pergunta:
    pergunta = pergunta.strip()

    if pergunta:
        st.session_state.historico.append({"tipo": "usuario", "texto": pergunta})

        texto_resposta = gerar_resposta(pergunta)

        st.session_state.historico.append({"tipo": "ia", "texto": texto_resposta})

        st.rerun()
