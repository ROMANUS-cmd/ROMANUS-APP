import streamlit as st
from google import genai

st.set_page_config(page_title="ROMANUS", layout="wide")

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.title("ROMANUS")
st.subheader("A IA que não passa pano.")

pergunta = st.text_input("Digite sua ordem:")

if pergunta:
    resposta = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=pergunta,
    )
    st.write(resposta.text)
