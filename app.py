import os
import re
import time
import html
import requests
import streamlit as st
from datetime import datetime
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup
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

TAMANHO_CHUNK = 1800
SOBREPOSICAO_CHUNK = 250
TOP_CHUNKS = 12
TOP_LINKS_WEB = 5
MIN_TEXTO_WEB = 500
SCORE_MINIMO_BASE = 35

PALAVRAS_IGNORADAS = {
    "a", "o", "e", "de", "da", "do", "das", "dos", "um", "uma",
    "em", "por", "para", "com", "sem", "que", "como", "qual",
    "quais", "onde", "quando", "isso", "essa", "esse", "sobre",
    "as", "os", "ao", "aos", "na", "no", "nas", "nos",
    "bom", "boa", "dia", "tarde", "noite", "oi", "ola", "olá"
}

DOMINIOS_CONFIAVEIS = [
    "gov.br",
    "planalto.gov.br",
    "in.gov.br",
    "camara.leg.br",
    "senado.leg.br",
    "stf.jus.br",
    "cnj.jus.br",
    "sp.gov.br",
    "alesp.sp.gov.br",
    "bombeiros.sp.gov.br",
    "policiamilitar.sp.gov.br",
    "lexml.gov.br",
    "ibge.gov.br",
    "bcb.gov.br",
    "receita.fazenda.gov.br",
    "presidencia.gov.br",
    "gov"
]

HEADERS_PADRAO = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36"
    )
}

# =========================================================
# ESTILO VISUAL
# =========================================================
st.markdown("""
<style>
[data-testid="stHeader"] {
    background: transparent !important;
}

.main .block-container {
    max-width: 1100px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}

.romanus-wrap {
    text-align: center;
    margin-top: 1rem;
    margin-bottom: 2rem;
}

.romanus-title {
    font-size: 52px;
    font-weight: 900;
    margin-bottom: 0.2rem;
}

.romanus-subtitle {
    font-size: 22px;
    opacity: 0.88;
    margin-bottom: 1rem;
}

.romanus-slogan {
    font-size: 18px;
    opacity: 0.76;
    margin-bottom: 2rem;
}

.bloco-resposta {
    border: 1px solid #d9d9d9;
    border-radius: 12px;
    padding: 18px;
    background: #fafafa;
    white-space: pre-wrap;
    font-size: 18px;
    line-height: 1.6;
}

.debug-box {
    border: 1px dashed #999;
    border-radius: 10px;
    padding: 12px;
    background: #fcfcfc;
    font-size: 14px;
    white-space: pre-wrap;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# SESSÃO HTTP
# =========================================================
@st.cache_resource
def criar_sessao_http():
    sessao = requests.Session()
    sessao.headers.update(HEADERS_PADRAO)
    return sessao

# =========================================================
# LEITURA DOS ARQUIVOS
# =========================================================
def extrair_texto_txt(caminho_txt: str) -> str:
    try:
        with open(caminho_txt, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return ""

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
# FUNÇÕES DE APOIO
# =========================================================
def normalizar_termos(texto: str):
    return [
        t for t in re.findall(r"\w+", (texto or "").lower())
        if len(t) >= 2 and t not in PALAVRAS_IGNORADAS
    ]

def normalizar_texto(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "")).strip()

def pergunta_pede_lista(pergunta: str) -> bool:
    p = (pergunta or "").lower()
    gatilhos = [
        "quais", "lista", "rol", "enumere", "enumeração",
        "medidas", "requisitos", "itens", "critérios",
        "quais são", "quais as", "defina", "definição"
    ]
    return any(g in p for g in gatilhos)

def dividir_em_chunks(texto: str, tamanho: int = TAMANHO_CHUNK, sobreposicao: int = SOBREPOSICAO_CHUNK):
    if not texto:
        return []

    texto = texto.strip()
    chunks = []

    inicio = 0
    while inicio < len(texto):
        fim = min(len(texto), inicio + tamanho)
        chunk = texto[inicio:fim].strip()
        if chunk:
            chunks.append(chunk)

        if fim >= len(texto):
            break

        inicio = max(0, fim - sobreposicao)

    return chunks

def extrair_referencia_local(texto: str):
    referencia = ""

    padroes = [
        r"(art\.?\s*\d+[º°]?)",
        r"(artigo\s+\d+[º°]?)",
        r"(item\s+\d+(\.\d+)*)",
        r"(capítulo\s+[ivxlcdm]+)",
        r"(capitulo\s+[ivxlcdm]+)",
        r"(§\s*\d+[º°]?)"
    ]

    texto_lower = (texto or "").lower()

    for padrao in padroes:
        m = re.search(padrao, texto_lower, re.IGNORECASE)
        if m:
            referencia = m.group(1)
            break

    return referencia

def score_nome_arquivo(nome: str, pergunta: str) -> int:
    score = 0
    nome_lower = nome.lower()
    pergunta_lower = pergunta.lower()

    palavras_fortes = [
        "decreto", "lei", "regulamento", "instrução", "it",
        "norma", "anexo", "quadro", "tabela", "medidas",
        "segurança", "incêndio", "capítulo", "artigo"
    ]

    for palavra in palavras_fortes:
        if palavra in nome_lower and palavra in pergunta_lower:
            score += 18

    if pergunta_pede_lista(pergunta):
        for palavra in ["anexo", "quadro", "tabela", "medidas", "regulamento", "decreto"]:
            if palavra in nome_lower:
                score += 16

    return score

def score_chunk(chunk: str, arquivo: str, pergunta: str) -> int:
    chunk_lower = chunk.lower()
    termos = normalizar_termos(pergunta)
    score = 0

    for termo in termos:
        score += chunk_lower.count(termo) * 4

    score += score_nome_arquivo(arquivo, pergunta)

    if pergunta_pede_lista(pergunta):
        gatilhos_lista = [
            "constituem", "incluem", "compreendem", "são medidas",
            "medidas de segurança contra incêndio",
            "deverá ser levado em consideração",
            "i -", "ii -", "iii -", "iv -", "v -", "vi -"
        ]
        for g in gatilhos_lista:
            if g in chunk_lower:
                score += 25

    if "decreto" in pergunta.lower() and "decreto" in arquivo.lower():
        score += 40

    if "medidas de segurança contra incêndio" in chunk_lower:
        score += 35

    if "artigo 20" in chunk_lower or "art. 20" in chunk_lower:
        score += 40

    if "capítulo viii" in chunk_lower or "capitulo viii" in chunk_lower:
        score += 20

    return score

def base_local_suficiente(trechos):
    if not trechos:
        return False

    melhor_score = max(t.get("score", 0) for t in trechos)
    return melhor_score >= SCORE_MINIMO_BASE

def escape_html(texto: str) -> str:
    return html.escape(texto or "")

# =========================================================
# RESPOSTA DIRETA SEM IA
# =========================================================
def resposta_data_hora_local(pergunta: str):
    p = (pergunta or "").lower().strip()

    gatilhos_dia = [
        "que dia é hoje",
        "qual o dia de hoje",
        "qual é o dia de hoje",
        "data de hoje",
        "hoje é que dia"
    ]

    gatilhos_hora = [
        "que horas são",
        "qual a hora",
        "qual é a hora"
    ]

    agora = datetime.now()

    if any(g in p for g in gatilhos_dia):
        data_formatada = agora.strftime("%d/%m/%Y")
        dia_semana = [
            "segunda-feira", "terça-feira", "quarta-feira",
            "quinta-feira", "sexta-feira", "sábado", "domingo"
        ][agora.weekday()]
        return (
            "RESPOSTA DIRETA:\n"
            f"Hoje é {data_formatada} ({dia_semana}).\n\n"
            "FUNDAMENTO:\n"
            "Data/hora do servidor da aplicação.\n\n"
            "GRAU DE CERTEZA:\n"
            "Direto do sistema."
        )

    if any(g in p for g in gatilhos_hora):
        hora_formatada = agora.strftime("%H:%M:%S")
        return (
            "RESPOSTA DIRETA:\n"
            f"Agora são {hora_formatada}.\n\n"
            "FUNDAMENTO:\n"
            "Relógio do servidor da aplicação.\n\n"
            "GRAU DE CERTEZA:\n"
            "Direto do sistema."
        )

    return None

def montar_resposta_base_local_direta(pergunta: str, trechos: list):
    if not trechos:
        return "Não localizei base suficiente para responder com segurança."

    melhor = trechos[0]
    arquivo = melhor.get("arquivo", "arquivo não identificado")
    referencia = melhor.get("referencia") or "não localizada"
    trecho = normalizar_texto(melhor.get("trecho", ""))

    if len(trecho) > 1800:
        trecho = trecho[:1800].strip() + "..."

    return (
        "RESPOSTA DIRETA:\n"
        "Localizei fundamento relevante na base local.\n\n"
        "FUNDAMENTO:\n"
        f"Arquivo: {arquivo}\n"
        f"Referência: {referencia}\n"
        f"Trecho: {trecho}\n\n"
        "GRAU DE CERTEZA:\n"
        "Base local suficiente.\n\n"
        "OBSERVAÇÃO TÉCNICA:\n"
        "Resposta montada diretamente a partir da base local, sem uso de modelo de IA."
    )

# =========================================================
# BUSCA WEB
# =========================================================
def dominio_confiavel(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
        return any(host == d or host.endswith("." + d) for d in DOMINIOS_CONFIAVEIS)
    except Exception:
        return False

def limpar_texto_html(html_texto: str) -> str:
    soup = BeautifulSoup(html_texto, "html.parser")

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    return normalizar_texto(soup.get_text(separator=" ", strip=True))

def extrair_texto_url(url: str, timeout: int = 15) -> str:
    try:
        sessao = criar_sessao_http()
        resp = sessao.get(url, timeout=timeout)
        resp.raise_for_status()
        texto = limpar_texto_html(resp.text)
        return texto
    except Exception:
        return ""

def gerar_trecho_relevante(texto: str, pergunta: str, tamanho: int = 1300) -> str:
    if not texto:
        return ""

    termos = [t.lower() for t in re.findall(r"\w+", pergunta) if len(t) >= 4]
    texto_lower = texto.lower()

    melhor_pos = 0
    melhor_score = -1

    for termo in termos:
        pos = texto_lower.find(termo)
        if pos != -1:
            janela = texto_lower[max(0, pos - 600): pos + 600]
            score = sum(1 for t in termos if t in janela)
            if score > melhor_score:
                melhor_score = score
                melhor_pos = pos

    inicio = max(0, melhor_pos - tamanho // 2)
    fim = min(len(texto), inicio + tamanho)
    trecho = texto[inicio:fim]

    return normalizar_texto(trecho)

def pesquisar_links_web(pergunta: str, max_links: int = TOP_LINKS_WEB):
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(pergunta)}"

    try:
        sessao = criar_sessao_http()
        resp = sessao.get(url, timeout=20)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links = []

    for a in soup.select("a.result__a"):
        href = a.get("href")
        if href and href.startswith("http"):
            links.append(href)

    vistos = set()
    unicos = []
    for link in links:
        if link not in vistos:
            vistos.add(link)
            unicos.append(link)

    return unicos[:max_links]

def buscar_na_internet(pergunta: str, max_links: int = TOP_LINKS_WEB):
    links = pesquisar_links_web(pergunta, max_links=max_links)
    resultados = []

    for url in links:
        if not dominio_confiavel(url):
            continue

        texto = extrair_texto_url(url)
        if not texto or len(texto) < MIN_TEXTO_WEB:
            continue

        trecho = gerar_trecho_relevante(texto, pergunta)

        resultados.append({
            "url": url,
            "trecho": trecho,
            "texto": texto
        })

    return resultados

def montar_resposta_web_direta(pergunta: str, resultados_web: list):
    if not resultados_web:
        return (
            "Não localizei base suficiente para responder com segurança.\n\n"
            "OBSERVAÇÃO TÉCNICA:\n"
            "A pesquisa web não retornou fonte confiável utilizável."
        )

    linhas = []
    linhas.append("RESPOSTA DIRETA:")
    linhas.append("Foram localizadas fontes web confiáveis relacionadas ao tema. Seguem os trechos relevantes.\n")

    linhas.append("FUNDAMENTO:")
    for i, item in enumerate(resultados_web[:3], start=1):
        linhas.append(f"{i}. Fonte: {item['url']}")
        linhas.append(f"Trecho relevante: {item['trecho']}\n")

    linhas.append("GRAU DE CERTEZA:")
    linhas.append("Pesquisa web direta; exige conferência literal da fonte oficial.\n")

    linhas.append("OBSERVAÇÃO TÉCNICA:")
    linhas.append("Resposta montada por regras, sem uso de provedor de IA.")
    return "\n".join(linhas)

# =========================================================
# INDEXAÇÃO EM CHUNKS
# =========================================================
@st.cache_data(show_spinner=False)
def indexar_base_em_chunks():
    base = carregar_base_local()
    indice = []

    for doc in base:
        chunks = dividir_em_chunks(doc["texto"], TAMANHO_CHUNK, SOBREPOSICAO_CHUNK)

        for i, chunk in enumerate(chunks, start=1):
            indice.append({
                "arquivo": doc["arquivo"],
                "chunk_id": i,
                "texto": chunk,
                "texto_lower": chunk.lower()
            })

    return indice

# =========================================================
# BUSCA GLOBAL NA BASE
# =========================================================
def buscar_trechos_na_base(pergunta: str, top_chunks: int = TOP_CHUNKS):
    indice = indexar_base_em_chunks()
    resultados = []

    for item in indice:
        score = score_chunk(item["texto"], item["arquivo"], pergunta)

        if score > 0:
            resultados.append({
                "arquivo": item["arquivo"],
                "chunk_id": item["chunk_id"],
                "trecho": item["texto"],
                "score": score,
                "referencia": extrair_referencia_local(item["texto"])
            })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:top_chunks]

# =========================================================
# GERAÇÃO DE RESPOSTA
# =========================================================
def gerar_resposta(pergunta: str, modo_estrito: bool = True, pesquisar_web: bool = False):
    inicio = time.time()

    try:
        # 0) respostas diretas do sistema
        resposta_sistema = resposta_data_hora_local(pergunta)
        if resposta_sistema:
            tempo = round(time.time() - inicio, 2)
            return {
                "ok": True,
                "texto": resposta_sistema,
                "tempo": tempo,
                "trechos": [],
                "erro": "",
                "origem": "sistema",
                "fontes_web": []
            }

        # 1) base local
        trechos = buscar_trechos_na_base(pergunta, TOP_CHUNKS)
        base_suficiente = base_local_suficiente(trechos)

        if base_suficiente:
            texto = montar_resposta_base_local_direta(pergunta, trechos)
            tempo = round(time.time() - inicio, 2)

            return {
                "ok": True,
                "texto": texto,
                "tempo": tempo,
                "trechos": trechos,
                "erro": "",
                "origem": "base_local",
                "fontes_web": []
            }

        # 2) modo estrito
        if modo_estrito:
            tempo = round(time.time() - inicio, 2)
            return {
                "ok": True,
                "texto": "Não localizei base suficiente para responder com segurança.",
                "tempo": tempo,
                "trechos": trechos,
                "erro": "",
                "origem": "nenhuma",
                "fontes_web": []
            }

        # 3) internet direta
        if pesquisar_web:
            resultados_web = buscar_na_internet(pergunta, max_links=TOP_LINKS_WEB)

            if resultados_web:
                texto = montar_resposta_web_direta(pergunta, resultados_web)
                tempo = round(time.time() - inicio, 2)

                return {
                    "ok": True,
                    "texto": texto,
                    "tempo": tempo,
                    "trechos": trechos,
                    "erro": "",
                    "origem": "web_direta",
                    "fontes_web": [r["url"] for r in resultados_web]
                }

        tempo = round(time.time() - inicio, 2)
        return {
            "ok": True,
            "texto": "Não localizei base suficiente para responder com segurança.",
            "tempo": tempo,
            "trechos": trechos,
            "erro": "",
            "origem": "nenhuma",
            "fontes_web": []
        }

    except Exception as e:
        tempo = round(time.time() - inicio, 2)
        return {
            "ok": False,
            "texto": "",
            "tempo": tempo,
            "trechos": [],
            "erro": str(e),
            "origem": "erro",
            "fontes_web": []
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
# CONTROLES
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
    pesquisar_web = st.checkbox(
        "Pesquisar na internet se a base local não trouxer resposta suficiente",
        value=False
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
if st.button("INICIAR"):
    if not pergunta.strip():
        st.warning("Digite uma pergunta.")
    else:
        with st.spinner("ROMANUS consultando a base..."):
            resultado = gerar_resposta(
                pergunta,
                modo_estrito=modo_estrito,
                pesquisar_web=pesquisar_web
            )

        if not resultado["ok"]:
            st.error("Erro ao gerar resposta.")
            st.code(resultado["erro"])
        else:
            st.markdown("### Resposta")
            st.markdown(
                f'<div class="bloco-resposta">{escape_html(resultado["texto"])}</div>',
                unsafe_allow_html=True
            )

            if resultado.get("fontes_web"):
                st.markdown("### Fontes web")
                for fonte in resultado["fontes_web"]:
                    st.markdown(f"- {fonte}")

        if mostrar_debug:
            base_total = carregar_base_local()
            indice_total = indexar_base_em_chunks()
            arquivos_usados = [t["arquivo"] for t in resultado.get("trechos", [])]
            referencias = [t["referencia"] for t in resultado.get("trechos", []) if t.get("referencia")]

            melhor_score = 0
            if resultado.get("trechos"):
                melhor_score = max(t.get("score", 0) for t in resultado["trechos"])

            debug_texto = (
                f"Arquivos na base: {len(base_total)}\n"
                f"Chunks totais indexados: {len(indice_total)}\n"
                f"Trechos retornados para a resposta: {len(resultado.get('trechos', []))}\n"
                f"Arquivos usados: {arquivos_usados if arquivos_usados else 'Nenhum'}\n"
                f"Referências localizadas: {referencias if referencias else 'Nenhuma'}\n"
                f"Melhor score encontrado: {melhor_score}\n"
                f"Score mínimo para considerar a base suficiente: {SCORE_MINIMO_BASE}\n"
                f"Tempo de resposta: {resultado.get('tempo', 0)} s\n"
                f"Modo estrito: {'Ligado' if modo_estrito else 'Desligado'}\n"
                f"Pesquisa web: {'Ligada' if pesquisar_web else 'Desligada'}\n"
                f"Origem final da resposta: {resultado.get('origem', 'desconhecida')}"
            )

            st.markdown("### Diagnóstico")
            st.markdown(
                f'<div class="debug-box">{escape_html(debug_texto)}</div>',
                unsafe_allow_html=True
            )
