import streamlit as st
from google import genai
from PIL import Image

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="ROMANUS",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# ESTILO
# =========================================================
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: Arial, sans-serif;
}

[data-testid="stHeader"] {
    background: white !important;
    border-bottom: none !important;
    box-shadow: none !important;
}

.main .block-container {
    padding-top: 0.6rem !important;
    padding-bottom: 2rem !important;
    max-width: 900px;
}

.topo-romanus {
    background: white;
    padding: 0 10px;
    margin: -20px 0 10px 0;
}

.topo-romanus h1 {
    margin: 0;
    font-size: 30px;
    font-weight: 900;
    line-height: 1;
    color: #111111;
    letter-spacing: 1px;
}

.topo-romanus p {
    margin: 4px 0 0 0;
    font-size: 14px;
    color: #666;
}

hr {
    display: none !important;
}

[data-testid="stChatMessage"] {
    border-radius: 14px;
}

.diagnostico {
    background: #f6f6f6;
    border: 1px solid #e5e5e5;
    border-radius: 12px;
    padding: 12px;
    margin-top: 10px;
    font-size: 14px;
    color: #222;
}
</style>

<div class="topo-romanus">
    <h1>ROMANUS</h1>
    <p>A IA que não passa pano.</p>
</div>
""", unsafe_allow_html=True)

# =========================================================
# PROMPT BASE
# =========================================================
PROMPT_BASE = """
Você é ROMANUS, uma IA de respostas diretas, técnicas e objetivas.

IDENTIDADE
- Seu nome é ROMANUS.
- Você responde sempre em português do Brasil.
- Você é direta, técnica, objetiva e útil.
- Você não enrola.
- Você não floreia.
- Você não usa resposta genérica.
- Você não inventa fatos, artigos, leis, números, dispositivos ou fontes.

COMPORTAMENTO
- Quando perguntarem "quem é você?", responda:
  "Sou ROMANUS, uma IA de respostas diretas, técnicas e objetivas."
- Quando perguntarem "quem te criou?", responda:
  "Fui criada por um grupo de especialistas em inteligência artificial reunidos sob o nome ROMANUS.IA."
- Só mencione Google, Gemini, modelo, API, infraestrutura ou base técnica se o usuário perguntar explicitamente.
- Evite frases vagas.
- Priorize clareza, firmeza e utilidade prática.
- Se não tiver base suficiente, diga isso com honestidade.
- Nunca finja certeza.
- Nunca invente base legal.
- Nunca crie artigo de lei.
- Nunca apresente hipótese como se fosse fato.

ESTILO
- Frases curtas.
- Linguagem profissional.
- Comunicação objetiva.
- Tom firme, técnico e respeitoso.
- Sem bajulação.
- Sem excesso de formalismo.
- Sem ironia ofensiva.
- Sem arrogância.
- Sem impaciência.

POSTURA DE COMUNICAÇÃO
- Seja educada, respeitosa e profissional.
- Trate o usuário com cordialidade natural.
- Responda com clareza e objetividade.
- Evite respostas secas demais.
- Mesmo ao corrigir o usuário, faça isso com respeito.
- Demonstre disposição para ajudar, sem parecer servil.
- Pode usar expressões como:
  "Claro."
  "Entendido."
  "Certo."
  "Vou direto ao ponto."
  "Segue a resposta objetiva."
  "Posso organizar isso para você."

QUANDO NÃO SOUBER
- Diga de forma clara:
  "Não tenho segurança para afirmar isso."
  "Preciso de mais dados para responder com precisão."
  "Não localizei base suficiente para confirmar isso."

QUANDO O USUÁRIO AGRADECER
- Responda de forma simples:
  "De nada."
  "À disposição."
  "Sempre que precisar."
  "Fico à disposição."

TEMAS JURÍDICOS, ADMINISTRATIVOS E TÉCNICOS
- Sempre que a pergunta envolver tema jurídico, administrativo, técnico-normativo ou regulatório, responda com base em lei, decreto, norma, instrução técnica, regulamento ou ato oficial aplicável.
- Sempre que possível, cite expressamente:
  número da norma,
  ano,
  artigo, item ou dispositivo relevante.
- Quando houver hierarquia normativa, priorize:
  1. Constituição
  2. Lei complementar
  3. Lei ordinária
  4. Decreto
  5. Regulamento
  6. Instrução técnica
  7. Norma complementar aplicável
- Nunca invente artigo, inciso, item, número de norma ou entendimento.
- Se não houver segurança quanto ao fundamento, diga isso claramente.
- Quando a pergunta depender de norma estadual ou local, priorize a norma do ente competente.
- Em temas de segurança contra incêndio no Estado de São Paulo, priorize a legislação paulista e as Instruções Técnicas do Corpo de Bombeiros do Estado de São Paulo.
- Em respostas técnicas, diferencie com clareza:
  - o que é exigência legal;
  - o que é exigência regulamentar;
  - o que é exigência técnica;
  - o que é recomendação prática.
- Quando houver risco de interpretação controvertida, informe que a conclusão depende do caso concreto e da norma aplicável.

MODELO DE SAÍDA PREFERENCIAL
Quando couber, estruture assim:
- Resposta objetiva: [resposta direta]
- Fundamento: [norma, artigo, item ou dispositivo]
- Conclusão prática: [efeito prático]

REGRAS FINAIS
- Responda exatamente ao que foi perguntado.
- Não traga rodeios.
- Não aumente artificialmente a resposta.
- Se o usuário pedir resumo, resuma.
- Se pedir resposta completa, aprofunde.
- Se a pergunta for simples, responda de forma simples.
"""
# Role: Especialista Multidisciplinar de Alta Profile: Atuar como um consultor sênior, focado em lógica e Diretrizes Respostas Diretas: Elimine frases de cortesia excessiva ou introduções Vá direto ao ponto técnico.
2. de Dados: tabelas, listas e código para dados complexos.
3. Hierarquia Técnica: (ABNT), Decretos Estaduais SP) e legislações Tom de Voz: Profissional, assertivo e focado em resolução se a solução proposta é viável sob o ponto de vista da engenharia e da segurança Restrições:
- Nunca mencione modelo de linguagem.
- ambiguidade, a solução baseada na prática de mercado 2. Estrutura Sugerida (GitHub)
Para IA funcione no GitHub, recomendo a seguinte organização de arquivos:

*   **`README.md`**: Descrição de instalação.
* bibliotecas (ex: `openai`, `langchain`, `python-dotenv`).
*   **`main.py`**: O código principal que executa da IA.
*   **`.env`**: Arquivo para armazenar suas chaves de API (nunca suba este público; use o `.gitignore`).
* Para excluir pastas como `__pycache__` `.env`.

### o senhor for utilizar a API da OpenAI ou similar, utilize este esqueleto no `main.py`:

```python
import os
from OpenAI

# A chave deve estar de ambiente ou GitHub Actions
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def gerar_resposta(pergunta_comandante):
        messages=[
            {"role": "system",            {"role": "content":        ],
        temperature=0.2 # Baixa temperatura garante maior objetividade técnica
    )
    return response.choices[0].message.content

if __name__ == "__main__":
 = input("Comandante, insira a    print(gerar_resposta(prompt_usuario))

# =========================================================
# ESTADO
# =========================================================
if "historico" not in st.session_state:
    st.session_state.historico = []

if "ultimo_erro" not in st.session_state:
    st.session_state.ultimo_erro = ""

if "api_ok" not in st.session_state:
    st.session_state.api_ok = None

# =========================================================
# CLIENTE GEMINI
# =========================================================
def criar_cliente():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        if not api_key or not str(api_key).strip():
            raise ValueError("A chave GEMINI_API_KEY está vazia.")
        client = genai.Client(api_key=api_key)
        return client, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

client, erro_cliente = criar_cliente()

# =========================================================
# TESTE DE CONEXÃO
# =========================================================
def testar_api():
    if client is None:
        return False, erro_cliente or "Cliente não foi inicializado."

    try:
        resposta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Responda apenas: ok"
        )

        texto = getattr(resposta, "text", None)
        if texto and texto.strip():
            return True, ""
        return False, f"API respondeu sem texto útil: {resposta}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

if st.session_state.api_ok is None:
    ok, erro = testar_api()
    st.session_state.api_ok = ok
    st.session_state.ultimo_erro = erro

# =========================================================
# FUNÇÃO DE RESPOSTA
# =========================================================
def gerar_resposta(pergunta: str, imagem=None) -> str:
    pergunta = pergunta.strip()

    if not pergunta:
        return "Escreva uma pergunta."

    if client is None:
        return f"Erro ao inicializar o cliente da API: {erro_cliente}"

    try:
        conteudo = [f"{PROMPT_BASE}\n\nPergunta do usuário: {pergunta}"]

        if imagem is not None:
            conteudo.append(imagem)

        resposta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=conteudo if imagem is not None else conteudo[0]
        )

        texto = getattr(resposta, "text", None)

        if texto and texto.strip():
            st.session_state.ultimo_erro = ""
            return texto.strip()

        return f"Resposta recebida, mas sem texto útil: {resposta}"

    except Exception as e:
        erro_real = f"{type(e).__name__}: {e}"
        st.session_state.ultimo_erro = erro_real
        return f"Erro ao consultar o modelo: {erro_real}"

# =========================================================
# DIAGNÓSTICO
# =========================================================
with st.expander("Diagnóstico", expanded=False):
    if st.session_state.api_ok:
        st.success("API inicializada com sucesso.")
    else:
        st.error("Falha na inicialização ou consulta da API.")

    st.markdown(
        f"""
        <div class="diagnostico">
        <b>Status da API:</b> {"OK" if st.session_state.api_ok else "FALHA"}<br>
        <b>Modelo:</b> gemini-2.5-flash<br>
        <b>Último erro:</b> {st.session_state.ultimo_erro if st.session_state.ultimo_erro else "nenhum"}
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# HISTÓRICO
# =========================================================
for item in st.session_state.historico:
    role = "user" if item["tipo"] == "usuario" else "assistant"
    with st.chat_message(role):
        st.markdown(item["texto"])

# =========================================================
# ENVIO DE IMAGEM
# =========================================================
imagem = None

with st.expander("📷 Enviar imagem", expanded=False):
    uploaded_file = st.file_uploader(
        "Escolha uma imagem",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file is not None:
        try:
            imagem = Image.open(uploaded_file)
            st.image(imagem, caption="Imagem enviada", use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao abrir a imagem: {type(e).__name__}: {e}")

# =========================================================
# ENTRADA DO USUÁRIO
# =========================================================
pergunta = st.chat_input("Pergunte à ROMANUS...")

if pergunta:
    pergunta = pergunta.strip()

    if pergunta:
        st.session_state.historico.append({
            "tipo": "usuario",
            "texto": pergunta
        })

        with st.chat_message("user"):
            st.markdown(pergunta)

        with st.chat_message("assistant"):
            with st.spinner("Consultando..."):
                texto_resposta = gerar_resposta(pergunta, imagem)
                st.markdown(texto_resposta)

        st.session_state.historico.append({
            "tipo": "ia",
            "texto": texto_resposta
        })
