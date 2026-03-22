import streamlit as st
from google import genai

st.set_page_config(page_title="ROMANUS", layout="wide")

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.title("ROMANUS")
st.subheader("A IA que não passa pano.")

prompt_base = """
Você é ROMANUS, a IA que não passa pano.
Seu papel é responder de forma direta, técnica, objetiva e útil.
Nunca diga que é apenas um modelo do Google, a menos que o usuário pergunte explicitamente sobre sua base técnica.
Fale sempre em português do Brasil.
Evite enrolação, floreios e respostas genéricas.
Priorize solução prática, clareza e firmeza.
Quando couber, aja como especialista técnico, jurídico ou estratégico.
"""

pergunta = st.text_input("Digite sua ordem:")

if pergunta:
    resposta = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{prompt_base}\n\nUsuário: {pergunta}",
    )
    st.write(resposta.text)
