import os
import re
import time
import html
import unicodedata
from datetime import datetime
from urllib.parse import quote_plus, urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup
from pypdf import PdfReader


# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="ROMANUS - Sistema de Inteligência",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# CONFIGURAÇÕES GERAIS E PARAMETRIZAÇÃO TÉCNICA
# =========================================================
BASE_CONHECIMENTO_DIR = "base_conhecimento"
ARQUIVOS_SUPORTADOS = (".txt", ".pdf")

TAMANHO_CHUNK = 1800
SOBREPOSICAO_CHUNK = 250
TOP_DOCS = 6
TOP_CHUNKS = 10
TOP_LINKS_WEB = 5
MIN_TEXTO_WEB = 180
SCORE_MINIMO_BASE = 35
SCORE_MINIMO_WEB = 2

PALAVRAS_IGNORADAS = {
    "a", "o", "e", "de", "da", "do", "das", "dos", "um", "uma",
    "em", "por", "para", "com", "sem", "que", "como", "qual",
    "quais", "onde", "quando", "isso", "essa", "esse", "sobre",
    "as", "os", "ao", "aos", "na", "no", "nas", "nos",
    "bom", "boa", "dia", "tarde", "noite", "oi", "ola", "olá"
}

PALAVRAS_TECNICAS_BASE = {
    "incêndio", "incendio", "bombeiro", "bombeiros", "it", "instrução",
    "instrucao", "decreto", "regulamento", "medidas", "edificação",
    "edificacao", "área de risco", "area de risco", "rotas de fuga",
    "rota de fuga", "hidrante", "hidrantes", "extintor", "extintores",
    "sprinkler", "segurança contra incêndio", "seguranca contra incendio",
    "cbpmesp", "pmesp", "chuveiros", "chuveiro", "fumaca", "fumaça",
    "saida de emergencia", "saída de emergência", "sinalizacao",
    "sinalização", "mangotinhos", "carga de incendio", "carga de incêndio",
    "brigada", "clcb", "avcb", "fat", "vistoria"
}

DOMINIOS_CONFIAVEIS = [
    "gov.br", "sp.gov.br", "bombeiros.sp.gov.br", "policiamilitar.sp.gov.br",
    "planalto.gov.br", "in.gov.br", "camara.leg.br", "senado.leg.br",
    "alesp.sp.gov.br", "wikipedia.org", "abnt.org.br"
]

MAPA_ASSUNTOS_PRIORITARIOS = {
    "saida de emergencia": ["it 11", "saidas de emergencia"],
    "rota de fuga": ["it 11", "saidas de emergencia"],
    "sinalizacao de emergencia": ["it 20", "sinalizacao de emergencia"],
    "hidrantes": ["it 22", "sistemas de hidrantes"],
    "extintores": ["it 21", "sistema de extintores"],
    "chuveiros automaticos": ["it 23", "sistemas de chuveiros"],
    "controle de fumaca": ["it 15", "controle de fumaca"],
    "brigada de incendio": ["it 17", "brigada de incendio"]
}

HEADERS_PADRAO = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0 Safari/537.36"
}

# =========================================================
# ESTILO VISUAL (UI/UX)
# =========================================================
st.markdown("""
<style>
.main .block-container { max-width: 1100px; padding-top: 1.2rem; }
.romanus-title { font-size: 52px; font-weight: 900; text-align: center; color: #B22222; }
.romanus-subtitle { font-size: 20px; text-align: center; opacity: 0.8; margin-bottom: 2rem; }
.bloco-resposta { 
    border-left: 5px solid #B22222; 
    border-radius: 8px; 
    padding: 20px; 
    background: #fdfdfd; 
    box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    font-size: 17px;
    line-height: 1.6;
}
.debug-box { font-size: 12px; color: #666; background: #eee; padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# UTILITÁRIOS DE TEXTO
# =========================================================
def remover_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")

def texto_norm(texto: str) -> str:
    texto = remover_acentos((texto or "").lower())
    texto = re.sub(r"[^a-z0-9/\-º°\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()

def normalizar_termos(texto: str):
    return [t for t in re.findall(r"\w+", texto_norm(texto)) if len(t) >= 2 and t not in PALAVRAS_IGNORADAS]

def detectar_referencia(pergunta: str):
    p = texto_norm(pergunta)
    it_match = re.search(r"\bit\s*(?:n|nº|n°|no|numero)?\s*(\d{1,2})", p)
    decreto_match = re.search(r"\bdecreto\s*(?:n|nº|n°|no|numero)?\s*(\d{2,3}\.?\d{0,3})", p)
    
    ref = {"tipo": None, "val": None}
    if it_match:
        ref = {"tipo": "it", "val": it_match.group(1)}
    elif decreto_match:
        ref = {"tipo": "decreto", "val": decreto_match.group(1).replace(".", "")}
    return ref

# =========================================================
# CORE: BUSCA E INDEXAÇÃO
# =========================================================
@st.cache_data(show_spinner=False)
def carregar_e_indexar():
    base = []
    if not os.path.exists(BASE_CONHECIMENTO_DIR): return []
    for raiz, _, arquivos in os.walk(BASE_CONHECIMENTO_DIR):
        for arquivo in arquivos:
            if arquivo.lower().endswith(ARQUIVOS_SUPORTADOS):
                caminho = os.path.join(raiz, arquivo)
                texto = ""
                if arquivo.lower().endswith(".pdf"):
                    reader = PdfReader(caminho)
                    texto = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
                else:
                    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                        texto = f.read()
                
                if texto:
                    chunks = [texto[i:i+TAMANHO_CHUNK] for i in range(0, len(texto), TAMANHO_CHUNK - SOBREPOSICAO_CHUNK)]
                    for idx, c in enumerate(chunks):
                        base.append({"arquivo": arquivo, "texto": c, "texto_norm": texto_norm(c)})
    return base

def calcular_score(item, pergunta, ref):
    score = 0
    p_norm = texto_norm(pergunta)
    termos = normalizar_termos(pergunta)
    
    # Bônus de referência exata (IT ou Decreto)
    if ref["tipo"] and ref["val"] in item["texto_norm"]:
        score += 200
    
    # Bônus por combinação de termos (proximidade lógica)
    encontrados = [t for t in termos if t in item["texto_norm"]]
    score += len(encontrados) * 10
    
    if len(encontrados) > 2: score += 30 # Relevância por densidade de palavras-chave
    
    return score

# =========================================================
# WEB SEARCH
# =========================================================
def buscar_web(pergunta):
    resultados = []
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(pergunta + ' bombeiros sp')}"
        resp = requests.get(url, headers=HEADERS_PADRAO, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for res in soup.select(".result__body")[:3]:
            link = res.select_one(".result__a")["href"]
            snippet = res.select_one(".result__snippet").get_text()
            if any(dom in link for dom in DOMINIOS_CONFIAVEIS):
                resultados.append({"url": link, "trecho": snippet, "score": 5})
    except: pass
    return resultados

# =========================================================
# LÓGICA DE RESPOSTA HÍBRIDA (O Cérebro do ROMANUS)
# =========================================================
def montar_resposta_final(trechos_base, resultados_web, pergunta, ref):
    base_ok = len(trechos_base) > 0 and trechos_base[0]["score"] >= SCORE_MINIMO_BASE
    web_ok = len(resultados_web) > 0

    # Caso 1: Resposta Híbrida (Base + Web)
    if base_ok and web_ok:
        melhor = trechos_base[0]
        res = "### 🛡️ ANÁLISE INTEGRADA (FUSÃO DE DADOS)\n\n"
        res += f"**FUNDAMENTO LEGAL (Base Interna):**\n"
        res += f"> Conforme encontrado em **{melhor['arquivo']}**: {melhor['texto'][:800].strip()}...\n\n"
        res += f"**INFORMAÇÕES COMPLEMENTARES (Web):**\n"
        res += f"> {resultados_web[0]['trecho']}\n"
        res += f"*Fonte externa: {resultados_web[0]['url']}*\n\n"
        res += "---\n**PARECER TÉCNICO:** A base local do CBPMESP prevalece para decisões administrativas. A web serve apenas como referência técnica adicional."
        return res, "hibrida"

    # Caso 2: Apenas Base Local
    if base_ok:
        melhor = trechos_base[0]
        return f"### 📑 FUNDAMENTO EXCLUSIVO DA BASE LOCAL\n\n**Arquivo:** {melhor['arquivo']}\n\n**Conteúdo Identificado:**\n{melhor['texto'][:1200]}...", "base_local"

    # Caso 3: Apenas Web (com aviso)
    if web_ok:
        return f"### 🌐 PESQUISA EXTERNA (Sem correspondência na base local)\n\n{resultados_web[0]['trecho']}\n\n*Fonte: {resultados_web[0]['url']}*", "web_direta"

    return "Não localizei base técnica suficiente para responder com segurança.", "nenhuma"

# =========================================================
# INTERFACE STREAMLIT
# =========================================================
st.markdown('<div class="romanus-title">ROMANUS</div>', unsafe_allow_html=True)
st.markdown('<div class="romanus-subtitle">Inteligência Operacional - CBPMESP</div>', unsafe_allow_html=True)

pergunta = st.text_area("Digite sua ordem ou dúvida técnica:", height=100)

if st.button("EXECUTAR ANÁLISE"):
    if not pergunta:
        st.warning("Comandante, insira uma pergunta.")
    else:
        with st.spinner("Analisando ITs, Decretos e Fontes Web..."):
            # 1. Carrega base
            indice = carregar_e_indexar()
            ref = detectar_referencia(pergunta)
            
            # 2. Busca na Base Local
            scores_base = []
            for item in indice:
                s = calcular_score(item, pergunta, ref)
                if s > 0:
                    scores_base.append({**item, "score": s})
            scores_base.sort(key=lambda x: x["score"], reverse=True)
            
            # 3. Busca na Web
            resultados_web = buscar_web(pergunta)
            
            # 4. Gera Resposta
            texto_final, origem = montar_resposta_final(scores_base[:3], resultados_web, pergunta, ref)
            
            # 5. Exibe
            st.markdown(f'<div class="bloco-resposta">{texto_final}</div>', unsafe_allow_html=True)
            
            # 6. Debug
            with st.expander("Diagnóstico do Sistema"):
                st.write(f"Origem da decisão: {origem}")
                st.write(f"Referência detectada: {ref}")
                if scores_base: st.write(f"Melhor score base: {scores_base[0]['score']}")
