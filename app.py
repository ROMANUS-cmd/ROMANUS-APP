import os
import re
import time
import streamlit as st
from google import genai
from pypdf import PdfReader

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="ROMANUS",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# CONFIGURAÇÕES GERAIS
# =========================================================
BASE_CONHECIMENTO_DIR = "base_conhecimento"
ARQUIVOS_SUPORTADOS = (".txt", ".pdf")
MAX_TRECHO_POR_DOCUMENTO = 2500
TOP_K = 3

# Troque aqui se quiser outro modelo
MODELO_GEMINI = "gemini-2.5-flash"

# =========================================================
# PROMPT PRINCIPAL
# =========================================================
PROMPT_SISTEMA = """
Você é ROMANUS, uma inteligência artificial técnica, objetiva e confiável.

IDENTIDADE
Seu nome é ROMANUS.
Seu posicionamento é: "A IA que não passa pano."
Seu papel é fornecer respostas diretas, técnicas, jurídicas, administrativas e operacionais, com máxima precisão e sem floreios.
Seu estilo deve ser firme, claro, profissional, disciplinado e eficiente.
Sarcasmo leve e inteligente só é permitido quando não comprometer a seriedade técnica.

MISSÃO
Sua missão é responder prioritariamente com base na base local fornecida pelo sistema.
Você deve priorizar:
- exatidão;
- fidelidade ao texto localizado;
- utilidade prática;
- clareza operacional;
- honestidade sobre limites.

REGRAS ABSOLUTAS
1. Nunca invente leis, artigos, itens, subitens, datas, normas, entendimentos, citações ou fatos.
2. Nunca afirme que encontrou algo se isso não constar na base recebida.
3. Nunca trate hipótese como fato.
4. Nunca complete lacunas com suposição disfarçada de certeza.
5. Nunca distorça o conteúdo localizado.
6. Se não houver base suficiente, diga isso claramente.
7. Se houver dúvida relevante, deixe a incerteza explícita.
8. Sempre prefira precisão a velocidade.
9. Sempre prefira resposta exata a texto longo e genérico.
10. Sempre responda em português do Brasil.

PRIORIDADE DE CONSULTA
A ordem correta é:
1. primeiro, analisar a base local enviada no contexto;
2. segundo, responder com base nessa base;
3. terceiro, apenas complementar com conhecimento geral se a base for insuficiente e isso não contrariar a base;
4. se não for possível responder com segurança, informar a limitação.

COMO USAR A BASE LOCAL
Se o sistema fornecer trechos de documentos:
- trate isso como a fonte principal;
- responda com fidelidade ao conteúdo;
- cite o nome do arquivo, se estiver disponível;
- diferencie claramente:
  a) texto expresso;
  b) resumo fiel;
  c) interpretação mínima.

QUANDO HOUVER TEXTO EXPRESSO
Se a base trouxer resposta clara:
- responda de forma direta;
- preserve o sentido original;
- não acrescente requisito inexistente;
- não “melhore” juridicamente o que o texto não diz.

QUANDO A BASE FOR PARCIAL
Se a base trouxer apenas elementos relacionados:
- diga expressamente que não há resposta literal completa;
- apresente apenas conclusão parcial;
- identifique que se trata de interpretação mínima;
- não extrapole além do que o texto sustenta.

FRASES OBRIGATÓRIAS QUANDO NECESSÁRIO
Use estas fórmulas quando forem verdadeiras:
- "Não localizei base suficiente para responder com segurança."
- "A base consultada não trouxe resposta literal para esse ponto."
- "O texto localizado permite apenas conclusão parcial."
- "Não é possível confirmar isso sem extrapolar a base."
- "Não encontrei elemento suficiente para responder com precisão."

ESTILO DE RESPOSTA
A resposta deve ser:
- direta;
- técnica;
- clara;
- profissional;
- sem rodeios;
- sem bajulação;
- sem excesso de texto.

Evite:
- frases vagas;
- respostas genéricas;
- “depende” sem explicar do que depende;
- enrolação;
- falsa segurança.

ESTRUTURA PADRÃO
Quando houver base útil, use preferencialmente:

RESPOSTA DIRETA:
[resposta objetiva]

FUNDAMENTO:
[arquivo consultado]

OBSERVAÇÃO TÉCNICA:
[apenas se necessário]

Se a pergunta for simples, responda de forma simples.

CONDUTA EM PERGUNTAS JURÍDICAS E NORMATIVAS
- responda apenas com o que puder sustentar;
- cite fundamento sempre que possível;
- diferencie texto localizado de interpretação;
- nunca invente artigo;
- nunca use tom categórico sem base.

PROIBIÇÕES
É proibido:
- criar citações falsas;
- fingir pesquisa;
- omitir incerteza;
- esconder falta de base com texto bonito;
- contradizer a base local sem explicar;
- responder como se tivesse certeza quando não tem.

REGRA DE OURO
Na dúvida, seja honesta.
Melhor admitir limite do que entregar uma resposta errada com aparência bonita.

BORDÃO OPERACIONAL
ROMANUS não passa pano.
ROMANUS responde com base.
ROMANUS não inventa.
ROMANUS resolve.
""".strip()

# =========================================================
# ESTILO
# =========================================================
st.markdown("""
<style>
[data-testid="stHeader"] {
    background: transparent !important;
}

.main .block-container {
    max-width: 1000px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}

.romanus-wrap {
    text-align: center;
    margin-top: 1rem;
    margin-bottom: 2rem;
}

.romanus-title {
    font-size: 54px;
    font-weight: 900;
    margin-bottom: 0.2rem;
}

.romanus-subtitle {
    font-size: 22px;
    opacity: 0.85;
    margin-bottom: 1rem;
}

.romanus-slogan {
    font-size: 18px;
    opacity: 0.75;
    margin-bottom: 2rem;
}

.bloco-resposta {
    border: 1px solid #d9d9d9;
    border-radius: 12px;
    padding: 18px;
    background: #fafafa;
    white-space: pre-wrap;
}

.debug-box {
    border: 1px dashed #999;
    border-radius: 10px;
    padding: 12px;
    background: #fcfcfc;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# CLIENTE GEMINI
# =========================================================
@st.cache_resource
def criar_cliente():
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("A chave GEMINI_API_KEY não foi encontrada no secrets.")
    return genai.Client(api_key=api_key)

# =========================================================
# LEITURA DA BASE
# =========================================================
def extrair_texto_pdf(caminho_pdf: str) -> str:
    partes = []
    try:
        reader = PdfReader(caminho_pdf)
        for pagina in reader.pages:
            try:
                txt = pagina.extract_text()
                if txt:
                    partes.append(txt)
            except Exception:
                continue
    except Exception:
        return ""
    return "\n".join(partes).strip()

def extrair_texto_txt(caminho_txt: str) -> str:
    try:
        with open(caminho_txt, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return ""

@st.cache_data(show_spinner=False)
def carregar_base_local():
    base = []

    if not os.path.exists(BASE_CONHECIMENTO_DIR):
        return base

    for raiz, _, arquivos in os.walk(BASE_CONHECIMENTO_DIR):
        for arquivo in arquivos:
            if not arquivo.lower().endswith(ARQUIVOS_SUPORTADOS):
                continue

            caminho = os.path.join(raiz, arquivo)
            nome_relativo = os.path.relpath(caminho, BASE_CONHECIMENTO_DIR)

            texto = ""
            if arquivo.lower().endswith(".txt"):
                texto = extrair_texto_txt(caminho)
            elif arquivo.lower().endswith(".pdf"):
                texto = extrair_texto_pdf(caminho)

            if texto:
                base.append({
                    "arquivo": nome_relativo,
                    "texto": texto,
                    "texto_lower": texto.lower()
                })

    return base

# =========================================================
# BUSCA NA BASE
# =========================================================
def limpar_pergunta(texto: str):
    return re.findall(r"\w+", texto.lower())

def buscar_na_base(pergunta: str, top_k: int = TOP_K):
    base = carregar_base_local()
    if not base:
        return []

    ignoradas = {
        "a", "o", "e", "de", "da", "do", "das", "dos", "um", "uma",
        "em", "por", "para", "com", "sem", "que", "como", "qual",
        "quais", "onde", "quando", "isso", "essa", "esse", "sobre",
        "bom", "boa", "dia", "tarde", "noite", "oi", "ola", "olá"
    }

    termos = [t for t in limpar_pergunta(pergunta) if len(t) >= 3 and t not in ignoradas]
    if not termos:
        return []

    resultados = []

    for item in base:
        nome = item["arquivo"].lower()
        texto = item["texto_lower"]
        score = 0

        for termo in termos:
            score += nome.count(termo) * 20
            score += texto.count(termo) * 3

        pergunta_lower = pergunta.lower().strip()
        if pergunta_lower and pergunta_lower in texto:
            score += 100

        if score > 0:
            resultados.append({
                "arquivo": item["arquivo"],
                "texto": item["texto"],
                "score": score
            })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:top_k]

def montar_contexto(resultados):
    if not resultados:
        return "Nenhum conteúdo relevante foi localizado na base local."

    blocos = []
    for i, item in enumerate(resultados, start=1):
        trecho = item["texto"][:MAX_TRECHO_POR_DOCUMENTO]
        bloco = (
            f"[DOCUMENTO {i}]\n"
            f"ARQUIVO: {item['arquivo']}\n"
            f"TRECHO:\n{trecho}\n"
        )
        blocos.append(bloco)

    return "\n\n".join(blocos)

# =========================================================
# CHAMADA AO MODELO
# =========================================================
def gerar_resposta(pergunta: str):
    cliente = criar_cliente()

    resultados = buscar_na_base(pergunta, TOP_K)
    contexto = montar_contexto(resultados)

    prompt_final = f"""
{PROMPT_SISTEMA}

PERGUNTA DO USUÁRIO:
{pergunta}

BASE LOCAL LOCALIZADA:
{contexto}

INSTRUÇÕES FINAIS
1. Priorize integralmente a base local.
2. Se a base responder, responda com base nela.
3. Cite os arquivos usados, se possível.
4. Não invente fundamento.
5. Se a base não responder com segurança, diga isso expressamente.
6. Não esconda limitação com texto bonito.
""".strip()

    inicio = time.time()

    try:
        resposta = cliente.models.generate_content(
            model=MODELO_GEMINI,
            contents=prompt_final
        )

        tempo = round(time.time() - inicio, 2)

        texto = ""
        if hasattr(resposta, "text") and resposta.text:
            texto = resposta.text.strip()

        if not texto:
            texto = "Não houve resposta textual do modelo."

        return {
            "ok": True,
            "texto": texto,
            "tempo": tempo,
            "resultados": resultados,
            "erro": ""
        }

    except Exception as e:
        tempo = round(time.time() - inicio, 2)
        return {
            "ok": False,
            "texto": "",
            "tempo": tempo,
            "resultados": resultados,
            "erro": str(e)
        }

# =========================================================
# CABEÇALHO
# =========================================================
st.markdown("""
<div class="romanus-wrap">
    <div class="romanus-title">ROMANUS</div>
    <div class="romanus-subtitle">A IA que não passa pano.</div>
    <div class="romanus-slogan">Respostas diretas. Soluções reais.</div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# CONTROLE
# =========================================================
with st.expander("Configuração", expanded=False):
    modo_estrito = st.checkbox(
        "Modo estrito (responder só com base local, sem improvisar)",
        value=True
    )
    mostrar_debug = st.checkbox(
        "Mostrar diagnóstico técnico",
        value=True
    )

# =========================================================
# ENTRADA
# =========================================================
pergunta = st.text_area(
    "Digite sua ordem:",
    height=140,
    placeholder="O que você precisa resolver hoje?"
)

# =========================================================
# EXECUÇÃO
# =========================================================
if st.button("INICIAR", use_container_width=False):
    if not pergunta.strip():
        st.warning("Digite uma pergunta.")
    else:
        with st.spinner("ROMANUS analisando a base..."):
            resultado = gerar_resposta(pergunta)

        if not resultado["ok"]:
            st.error("Erro ao gerar resposta.")
            st.code(resultado["erro"])
        else:
            resposta_final = resultado["texto"]

            if modo_estrito and "Nenhum conteúdo relevante foi localizado na base local." in montar_contexto(resultado["resultados"]):
                resposta_final = "Não localizei base suficiente para responder com segurança."

            st.markdown("### Resposta")
            st.markdown(f'<div class="bloco-resposta">{resposta_final}</div>', unsafe_allow_html=True)

        if mostrar_debug:
            st.markdown("### Diagnóstico")
            arquivos = [r["arquivo"] for r in resultado["resultados"]] if "resultados" in resultado else []
            base_total = carregar_base_local()

            debug_texto = f"""
Arquivos na base: {len(base_total)}
Arquivos usados na busca: {len(arquivos)}
Lista de arquivos usados: {arquivos if arquivos else "Nenhum"}
Modelo: {MODELO_GEMINI}
Tempo de resposta: {resultado.get("tempo", 0)} s
Modo estrito: {"Ligado" if modo_estrito else "Desligado"}
"""
            st.markdown(f'<div class="debug-box">{debug_texto}</div>', unsafe_allow_html=True)
