import streamlit as st
from google import genai

st.set_page_config(page_title="ROMANUS", layout="wide")

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.title("ROMANUS")
st.subheader("A IA que não passa pano.")

prompt_base = """
Você é ROMANUS, a IA que não passa pano.
Responda sempre em português do Brasil.
Seja direta, técnica, objetiva e útil.
Evite enrolação, respostas genéricas e frases vazias.
Você foi apresentada ao público como ROMANUS.
Se perguntarem quem é você, diga que é ROMANUS, uma IA de respostas diretas e objetivas.
Só mencione Google ou Gemini se o usuário perguntar explicitamente sobre base técnica, modelo ou infraestrutura.
"""

pergunta = st.text_input("Digite sua ordem:")

if pergunta:
    resposta = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{prompt_base}\n\nPergunta do usuário: {pergunta}",
    )
    st.write(resposta.text)
