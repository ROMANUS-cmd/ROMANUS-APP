import os
import re
import time
import html
import unicodedata
from datetime import datetime
from urllib.parse import quote_plus, urlparse, unquote

import requests
import streamlit as st
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
TOP_DOCS = 8
TOP_CHUNKS = 12
TOP_LINKS_WEB = 8
MIN_TEXTO_WEB = 180
SCORE_MINIMO_BASE = 35
SCORE_MINIMO_WEB = 2
TIMEOUT_PADRAO = 18

PALAVRAS_IGNORADAS = {
    "a", "o", "e", "de", "da", "do", "das", "dos", "um", "uma",
    "em", "por", "para", "com", "sem", "que", "como", "qual",
    "quais", "onde", "quando", "isso", "essa", "esse", "sobre",
    "as", "os", "ao", "aos", "na", "no", "nas", "nos",
    "bom", "boa", "dia", "tarde", "noite", "oi", "ola", "olá",
    "me", "diga", "pesquise", "internet", "quero", "saber",
    "cidade", "cidades", "estado", "estados", "sul", "norte",
    "leste", "oeste", "paulo", "sao", "são", "brasil", "brasileiro",
    "brasileira", "atual", "nome", "lista", "quaisas", "quale"
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
    "avcb", "clcb", "brigada", "detecção", "deteccao", "alarme",
    "resistencia ao fogo", "compartimentacao", "lotacao", "lotação",
    "saidas", "edificacao", "protecao passiva", "proteção passiva",
    "compartimentação", "resistência ao fogo", "proteção ativa",
    "protecao ativa", "hidrantes urbanos", "controle de fumaca",
    "controle de fumaça", "saídas de emergência"
}

DOMINIOS_CONFIAVEIS = [
    "gov.br",
    "planalto.gov.br",
    "in.gov.br",
    "camara.leg.br",
    "senado.leg.br",
    "stf.jus.br",
    "stj.jus.br",
    "cnj.jus.br",
    "tst.jus.br",
    "tre-sp.jus.br",
    "sp.gov.br",
    "alesp.sp.gov.br",
    "bombeiros.sp.gov.br",
    "policiamilitar.sp.gov.br",
    "lexml.gov.br",
    "ibge.gov.br",
    "bcb.gov.br",
    "presidencia.gov.br",
    "receita.fazenda.gov.br",
    "wikipedia.org",
    "wikidata.org",
    "britannica.com",
    "encyclopedia.com",
    "bbc.com",
    "reuters.com",
    "apnews.com",
    "g1.globo.com",
    "uol.com.br",
    "mundoeducacao.uol.com.br",
    "brasilescola.uol.com.br",
    "cnnbrasil.com.br",
    "nexo.jor.br",
    "worldbank.org",
    "imf.org",
    "who.int",
    "un.org",
    "unesco.org",
    "ourworldindata.org",
    "nih.gov",
    "cdc.gov",
    "europa.eu",
    "consilium.europa.eu",
    "ec.europa.eu"
]

DOMINIOS_ALTISSIMA_CONFIANCA = [
    "gov.br",
    "planalto.gov.br",
    "in.gov.br",
    "camara.leg.br",
    "senado.leg.br",
    "stf.jus.br",
    "sp.gov.br",
    "alesp.sp.gov.br",
    "bombeiros.sp.gov.br",
    "ibge.gov.br",
    "bcb.gov.br",
    "presidencia.gov.br",
    "wikipedia.org",
    "britannica.com",
    "reuters.com",
    "apnews.com",
    "who.int",
    "un.org"
]

MAPA_ASSUNTOS_PRIORITARIOS = {
    "saida de emergencia": ["it 11", "saidas de emergencia"],
    "saidas de emergencia": ["it 11", "saidas de emergencia"],
    "rota de fuga": ["it 11", "saidas de emergencia"],
    "rotas de fuga": ["it 11", "saidas de emergencia"],
    "sinalizacao de emergencia": ["it 20", "sinalizacao de emergencia"],
    "hidrantes": ["it 22", "sistemas de hidrantes e de mangotinhos"],
    "mangotinhos": ["it 22", "sistemas de hidrantes e de mangotinhos"],
    "chuveiros automaticos": ["it 23", "sistemas de chuveiros automaticos"],
    "controle de fumaca": ["it 15", "controle de fumaca"],
    "brigada": ["it 17", "brigada de incendio"],
    "loteacao": ["it 34", "hidrantes urbanos"],
    "loteamento": ["it 34", "hidrantes urbanos"]
}

HEADERS_PADRAO = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
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

.fonte-box {
    border: 1px solid #e3e3e3;
    border-radius: 10px;
    padding: 12px;
    background: #fff;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# UTILITÁRIOS
# =========================================================
def escape_html(texto: str) -> str:
    return html.escape(texto or "")

def remover_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(c) != "Mn"
    )

def normalizar_texto(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "")).strip()

def texto_norm(texto: str) -> str:
    texto = remover_acentos((texto or "").lower())
    texto = re.sub(r"[^a-z0-9/\-º°\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto

def normalizar_termos(texto: str):
    return [
        t for t in re.findall(r"\w+", texto_norm(texto))
        if len(t) >= 2 and t not in PALAVRAS_IGNORADAS
    ]

def limitar_texto(texto: str, max_chars: int = 1200) -> str:
    texto = normalizar_texto(texto)
    if len(texto) <= max_chars:
        return texto
    return texto[:max_chars].rstrip() + "..."

def pergunta_pede_lista(pergunta: str) -> bool:
    p = texto_norm(pergunta)
    gatilhos = [
        "quais", "lista", "rol", "enumere", "enumeracao",
        "medidas", "requisitos", "itens", "criterios",
        "quais sao", "quais as", "defina", "definicao"
    ]
    return any(g in p for g in gatilhos)

def pergunta_tecnica_da_base(pergunta: str) -> bool:
    p = texto_norm(pergunta)
    return any(remover_acentos(t) in p for t in PALAVRAS_TECNICAS_BASE)

def pergunta_pede_objeto_norma(pergunta: str) -> bool:
    p = texto_norm(pergunta)
    gatilhos = [
        "o que regulamenta",
        "o que trata",
        "qual o objeto",
        "qual o objetivo",
        "do que trata",
        "o que dispoe",
        "o que estabelece",
        "a que se refere"
    ]
    return any(g in p for g in gatilhos)

def pergunta_pede_identidade(pergunta: str) -> bool:
    p = texto_norm(pergunta)
    gatilhos = [
        "qual e o seu nome",
        "qual o seu nome",
        "como e o seu nome",
        "quem e voce",
        "como voce se chama"
    ]
    return any(g in p for g in gatilhos)

def pergunta_geral_web(pergunta: str) -> bool:
    if pergunta_tecnica_da_base(pergunta):
        return False
    return True

def detectar_assunto_prioritario(pergunta: str):
    p = texto_norm(pergunta)

    for chave, pistas in MAPA_ASSUNTOS_PRIORITARIOS.items():
        if chave in p:
            return {"chave": chave, "pistas": pistas}

    return None

def eh_url_valida(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False

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

            if arquivo.lower().endswith(".txt"):
                texto = extrair_texto_txt(caminho)
            else:
                texto = extrair_texto_pdf(caminho)

            if texto:
                base.append({
                    "arquivo": nome_relativo,
                    "arquivo_norm": texto_norm(nome_relativo),
                    "texto": texto,
                    "texto_norm": texto_norm(texto)
                })

    return base

# =========================================================
# DETECTOR DE REFERÊNCIA EXATA
# =========================================================
def detectar_referencia(pergunta: str):
    p = texto_norm(pergunta)

    it_match = re.search(r"\bit\s*(?:n|nº|n°|no|numero)?\s*(\d{1,2})[/-](\d{2})\b", p)
    decreto_match = re.search(r"\bdecreto\s*(?:n|nº|n°|no|numero)?\s*(\d{1,3}(?:\.\d{3})*)[/-](\d{2})\b", p)
    artigo_match = re.search(r"\bart(?:igo)?\.?\s*(\d+[a-z]?)\b", p)
    item_match = re.search(r"\bitem\s+(\d+(?:\.\d+)*)\b", p)

    ref = {
        "tipo": None,
        "it_num": None,
        "it_ano": None,
        "decreto_num": None,
        "decreto_ano": None,
        "artigo": None,
        "item": None
    }

    if it_match:
        ref["tipo"] = "it"
        ref["it_num"] = it_match.group(1)
        ref["it_ano"] = it_match.group(2)

    if decreto_match:
        ref["tipo"] = "decreto"
        ref["decreto_num"] = decreto_match.group(1)
        ref["decreto_ano"] = decreto_match.group(2)

    if artigo_match:
        ref["artigo"] = artigo_match.group(1)

    if item_match:
        ref["item"] = item_match.group(1)

    return ref

def variantes_it(it_num: str, it_ano: str):
    n = str(int(it_num))
    n2 = f"{int(it_num):02d}"
    return [
        f"it {n}/{it_ano}",
        f"it {n}-{it_ano}",
        f"it nº {n}-{it_ano}",
        f"it n {n}-{it_ano}",
        f"it no {n}-{it_ano}",
        f"it {n2}/{it_ano}",
        f"it {n2}-{it_ano}",
        f"it nº {n2}-{it_ano}",
        f"it n {n2}-{it_ano}",
        f"it no {n2}-{it_ano}"
    ]

def variantes_decreto(num: str, ano: str):
    num = num.replace(",", ".")
    return [
        f"decreto {num}/{ano}",
        f"decreto {num}-{ano}",
        f"decreto nº {num}/{ano}",
        f"decreto nº {num}-{ano}",
        f"decreto n {num}/{ano}",
        f"decreto n {num}-{ano}"
    ]

# =========================================================
# SCORE DE DOCUMENTO
# =========================================================
def score_nome_arquivo(nome: str, pergunta: str) -> int:
    score = 0
    nome_lower = texto_norm(nome)
    pergunta_lower = texto_norm(pergunta)

    palavras_fortes = [
        "decreto", "lei", "regulamento", "instrucao", "it",
        "norma", "anexo", "quadro", "tabela", "medidas",
        "seguranca", "incendio", "capitulo", "artigo"
    ]

    for palavra in palavras_fortes:
        if palavra in nome_lower and palavra in pergunta_lower:
            score += 10

    if pergunta_pede_lista(pergunta):
        for palavra in ["anexo", "quadro", "tabela", "medidas", "regulamento", "decreto"]:
            if palavra in nome_lower:
                score += 8

    return score

def score_documento(doc, pergunta: str, ref: dict) -> int:
    score = 0
    arquivo_norm = doc["arquivo_norm"]
    termos = normalizar_termos(pergunta)

    if ref["tipo"] == "it" and ref["it_num"] and ref["it_ano"]:
        for v in variantes_it(ref["it_num"], ref["it_ano"]):
            if v in arquivo_norm:
                score += 500

        n = str(int(ref["it_num"]))
        n2 = f"{int(ref['it_num']):02d}"
        if f"it {n}" in arquivo_norm or f"it {n2}" in arquivo_norm:
            score += 80
        if ref["it_ano"] in arquivo_norm:
            score += 40

    if ref["tipo"] == "decreto" and ref["decreto_num"] and ref["decreto_ano"]:
        for v in variantes_decreto(ref["decreto_num"], ref["decreto_ano"]):
            if v in arquivo_norm:
                score += 500

        if ref["decreto_num"] in arquivo_norm:
            score += 80
        if ref["decreto_ano"] in arquivo_norm:
            score += 40

    assunto = detectar_assunto_prioritario(pergunta)
    if assunto:
        for pista in assunto["pistas"]:
            if pista in arquivo_norm:
                score += 180

    for termo in termos:
        if termo in arquivo_norm:
            score += 6

    score += score_nome_arquivo(doc["arquivo"], pergunta)

    if pergunta_tecnica_da_base(pergunta):
        if "it " in arquivo_norm or "decreto" in arquivo_norm:
            score += 10

    if not pergunta_tecnica_da_base(pergunta):
        if "it " in arquivo_norm or "decreto" in arquivo_norm:
            score -= 20

    if pergunta_pede_objeto_norma(pergunta) and ref["tipo"] in {"it", "decreto"}:
        score += 20

    return score

# =========================================================
# CHUNKS
# =========================================================
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
        r"(art\.?\s*\d+[a-zº°]?)",
        r"(artigo\s+\d+[a-zº°]?)",
        r"(item\s+\d+(\.\d+)*)",
        r"(capítulo\s+[ivxlcdm]+)",
        r"(capitulo\s+[ivxlcdm]+)",
        r"(§\s*\d+[º°]?)"
    ]

    texto_lower = texto_norm(texto)

    for padrao in padroes:
        m = re.search(padrao, texto_lower, re.IGNORECASE)
        if m:
            referencia = m.group(1)
            break

    return referencia

def chunk_parece_lixo(chunk: str) -> bool:
    t = normalizar_texto(chunk)
    if not t:
        return True

    digitos = sum(c.isdigit() for c in t)
    letras = sum(c.isalpha() for c in t)
    if digitos > letras and digitos > 40:
        return True

    palavras = re.findall(r"[A-Za-zÀ-ÿ]{2,}", t)
    if len(palavras) < 12:
        return True

    if re.search(r"(\d+[,\.\d]*\s+){8,}", t):
        return True

    return False

def score_chunk(chunk: str, arquivo: str, pergunta: str, ref: dict) -> int:
    chunk_norm = texto_norm(chunk)
    termos = normalizar_termos(pergunta)
    score = 0

    if chunk_parece_lixo(chunk):
        return -100

    for termo in termos:
        ocorrencias = chunk_norm.count(termo)
        if ocorrencias > 0:
            score += ocorrencias * 6

    score += score_nome_arquivo(arquivo, pergunta)

    if pergunta_pede_lista(pergunta):
        gatilhos_lista = [
            "constituem", "incluem", "compreendem", "sao medidas",
            "devera ser levado em consideracao", "devera ser levado em consideração",
            "i -", "ii -", "iii -", "iv -", "v -", "vi -"
        ]
        for g in gatilhos_lista:
            if g in chunk_norm:
                score += 10

    if pergunta_pede_objeto_norma(pergunta):
        gatilhos_objeto = [
            "esta instrucao tecnica",
            "fixa as condicoes",
            "estabelece as exigencias",
            "define as medidas",
            "disciplina",
            "regulamenta",
            "aplica se",
            "tem por objetivo",
            "objetivo",
            "finalidade"
        ]
        for g in gatilhos_objeto:
            if g in chunk_norm:
                score += 18

    if ref["artigo"]:
        alvo = f"art {ref['artigo']}"
        if alvo in chunk_norm or f"artigo {ref['artigo']}" in chunk_norm:
            score += 30

    if ref["item"]:
        if f"item {ref['item']}" in chunk_norm:
            score += 30

    if not pergunta_tecnica_da_base(pergunta):
        termos_tecnicos = [
            "incendio", "seguranca contra incendio", "hidrantes", "chuveiros",
            "edificacao", "edificacoes", "area de risco", "rotas de fuga",
            "brigada", "extintores", "alarme", "avcb", "clcb",
            "regulamento", "instrucao tecnica", "decreto"
        ]
        ocorrencias_tecnicas = sum(1 for t in termos_tecnicos if t in chunk_norm)
        score -= ocorrencias_tecnicas * 15

    return score

# =========================================================
# INDEXAÇÃO
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
                "arquivo_norm": doc["arquivo_norm"],
                "chunk_id": i,
                "texto": chunk,
                "texto_norm": texto_norm(chunk)
            })

    return indice

# =========================================================
# BUSCA NA BASE
# =========================================================
def buscar_documentos_candidatos(pergunta: str, top_docs: int = TOP_DOCS):
    base = carregar_base_local()
    ref = detectar_referencia(pergunta)
    docs = []

    for doc in base:
        score = score_documento(doc, pergunta, ref)
        if score > 0:
            docs.append({
                "arquivo": doc["arquivo"],
                "arquivo_norm": doc["arquivo_norm"],
                "score": score
            })

    docs.sort(key=lambda x: x["score"], reverse=True)
    return docs[:top_docs], ref

def buscar_trechos_na_base(pergunta: str, top_chunks: int = TOP_CHUNKS):
    docs_candidatos, ref = buscar_documentos_candidatos(pergunta, TOP_DOCS)
    if not docs_candidatos:
        return [], docs_candidatos, ref

    arquivos_prioritarios = {d["arquivo"] for d in docs_candidatos}
    indice = indexar_base_em_chunks()
    resultados = []

    for item in indice:
        if item["arquivo"] not in arquivos_prioritarios:
            continue

        score = score_chunk(item["texto"], item["arquivo"], pergunta, ref)
        if score <= 0:
            continue

        resultados.append({
            "arquivo": item["arquivo"],
            "chunk_id": item["chunk_id"],
            "trecho": item["texto"],
            "score": score,
            "referencia": extrair_referencia_local(item["texto"])
        })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:top_chunks], docs_candidatos, ref

def base_local_suficiente(trechos, pergunta: str, ref: dict):
    if not trechos:
        return False

    if not pergunta_tecnica_da_base(pergunta) and ref["tipo"] not in {"it", "decreto"}:
        return False

    termos = normalizar_termos(pergunta)
    if not termos and not ref["tipo"]:
        return False

    melhor = trechos[0]
    texto = texto_norm(melhor.get("trecho") or "")
    termos_presentes = sum(1 for t in termos if t in texto)
    melhor_score = melhor.get("score", 0)

    if ref["tipo"] in {"it", "decreto"}:
        return melhor_score >= 40

    minimo_termos = 2 if len(termos) <= 3 else 3
    return melhor_score >= SCORE_MINIMO_BASE and termos_presentes >= minimo_termos

def montar_resposta_base_local_direta(pergunta: str, trechos: list, houve_apoio_web: bool = False):
    if not trechos:
        return "Não localizei base suficiente para responder com segurança."

    melhor = trechos[0]
    arquivo = melhor.get("arquivo", "arquivo não identificado")
    referencia = melhor.get("referencia") or "não localizada"
    trecho = limitar_texto(melhor.get("trecho", ""), 1600)

    observacao = "Resposta montada diretamente a partir da base local."
    if houve_apoio_web:
        observacao += " Houve pesquisa web complementar, mas a base local permaneceu mais forte."

    cabecalho = (
        "Localizei na base local o fundamento mais provável sobre o objeto/finalidade da norma."
        if pergunta_pede_objeto_norma(pergunta)
        else "Localizei fundamento relevante na base local."
    )

    return (
        "RESPOSTA DIRETA:\n"
        f"{cabecalho}\n\n"
        "FUNDAMENTO:\n"
        f"Arquivo: {arquivo}\n"
        f"Referência: {referencia}\n"
        f"Trecho: {trecho}\n\n"
        "GRAU DE CERTEZA:\n"
        "Base local suficiente.\n\n"
        "OBSERVAÇÃO TÉCNICA:\n"
        f"{observacao}"
    )

# =========================================================
# RESPOSTAS DIRETAS DO SISTEMA
# =========================================================
def resposta_identidade(pergunta: str):
    if pergunta_pede_identidade(pergunta):
        return (
            "RESPOSTA DIRETA:\n"
            "Meu nome é ROMANUS.\n\n"
            "FUNDAMENTO:\n"
            "Identidade definida na própria aplicação.\n\n"
            "GRAU DE CERTEZA:\n"
            "Direto do sistema."
        )
    return None

def resposta_data_hora_local(pergunta: str):
    p = texto_norm(pergunta)

    gatilhos_dia = [
        "que dia e hoje",
        "qual o dia de hoje",
        "qual e o dia de hoje",
        "data de hoje",
        "hoje e que dia"
    ]

    gatilhos_hora = [
        "que horas sao",
        "qual a hora",
        "qual e a hora"
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

# =========================================================
# WEB
# =========================================================
def dominio_confiavel(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
        return any(
            host == d.replace("www.", "") or host.endswith("." + d.replace("www.", ""))
            for d in DOMINIOS_CONFIAVEIS
        )
    except Exception:
        return False

def dominio_altissima_confianca(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
        return any(
            host == d.replace("www.", "") or host.endswith("." + d.replace("www.", ""))
            for d in DOMINIOS_ALTISSIMA_CONFIANCA
        )
    except Exception:
        return False

def normalizar_link_resultado_busca(href: str) -> str:
    if not href:
        return ""

    href = href.strip()

    if href.startswith("//"):
        href = "https:" + href

    if href.startswith("/"):
        m = re.search(r"[?&](uddg|rut)=([^&]+)", href)
        if m:
            return unquote(m.group(2))
        return ""

    if href.startswith("http://") or href.startswith("https://"):
        try:
            parsed = urlparse(href)
            if "duckduckgo.com" in parsed.netloc:
                m = re.search(r"[?&](uddg|rut)=([^&]+)", href)
                if m:
                    return unquote(m.group(2))
            return href
        except Exception:
            return ""

    return ""

def limpar_texto_html(html_texto: str) -> str:
    soup = BeautifulSoup(html_texto, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()
    return normalizar_texto(soup.get_text(separator=" ", strip=True))

def extrair_texto_url(url: str, timeout: int = TIMEOUT_PADRAO) -> str:
    try:
        sessao = criar_sessao_http()
        resp = sessao.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()

        content_type = (resp.headers.get("Content-Type") or "").lower()
        if "pdf" in content_type:
            return ""

        return limpar_texto_html(resp.text)
    except Exception:
        return ""

def gerar_trecho_relevante(texto: str, pergunta: str, tamanho: int = 1200) -> str:
    if not texto:
        return ""

    termos = [t.lower() for t in re.findall(r"\w+", texto_norm(pergunta)) if len(t) >= 3]
    texto_lower = texto_norm(texto)

    melhor_pos = 0
    melhor_score = -1

    for termo in termos:
        pos = texto_lower.find(termo)
        if pos != -1:
            janela = texto_lower[max(0, pos - 500): pos + 500]
            score = sum(1 for t in termos if t in janela)
            if score > melhor_score:
                melhor_score = score
                melhor_pos = pos

    inicio = max(0, melhor_pos - tamanho // 2)
    fim = min(len(texto), inicio + tamanho)
    return normalizar_texto(texto[inicio:fim])

def score_resultado_web(texto: str, pergunta: str, url: str = "") -> int:
    termos = [t.lower() for t in re.findall(r"\w+", texto_norm(pergunta)) if len(t) >= 3]
    texto_lower = texto_norm(texto)
    score = 0

    for termo in termos:
        ocorrencias = texto_lower.count(termo)
        if ocorrencias > 0:
            score += min(ocorrencias, 5)

    pergunta_n = texto_norm(pergunta)

    if any(g in pergunta_n for g in ["presidente", "governador", "ministro", "prefeito"]):
        if any(t in texto_lower for t in ["presidente", "governador", "ministro", "prefeito"]):
            score += 3

    if dominio_altissima_confianca(url):
        score += 4
    elif dominio_confiavel(url):
        score += 2

    if len(texto) > 500:
        score += 1

    return score

def pesquisar_links_web(consulta: str, max_links: int = TOP_LINKS_WEB):
    sessao = criar_sessao_http()
    links = []

    urls_busca = [
        f"https://html.duckduckgo.com/html/?q={quote_plus(consulta)}",
        f"https://lite.duckduckgo.com/lite/?q={quote_plus(consulta)}"
    ]

    for url in urls_busca:
        try:
            resp = sessao.get(url, timeout=TIMEOUT_PADRAO)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = normalizar_link_resultado_busca(a.get("href", ""))
                if href and eh_url_valida(href):
                    links.append(href)
        except Exception:
            continue

        if links:
            break

    vistos = set()
    unicos = []
    for link in links:
        if link not in vistos:
            vistos.add(link)
            unicos.append(link)

    return unicos[:max_links]

def pesquisar_links_web_multicamadas(pergunta: str, max_links: int = TOP_LINKS_WEB):
    consultas = [
        pergunta,
        f'"{pergunta}"',
        f"{pergunta} wikipedia",
        f"{pergunta} noticia OR notícia OR news",
        f"{pergunta} explicação OR explicacao OR conceito"
    ]

    links_finais = []
    vistos = set()

    for consulta in consultas:
        links = pesquisar_links_web(consulta, max_links=max_links)

        for link in links:
            if link not in vistos:
                vistos.add(link)
                links_finais.append(link)

        if len(links_finais) >= max_links:
            break

    return links_finais[:max_links]

def buscar_wikipedia_direto(pergunta: str):
    p = texto_norm(pergunta)
    termo = ""

    gatilhos_diretos = ["quem e ", "quem foi ", "o que e ", "o que foi "]
    for g in gatilhos_diretos:
        if g in p:
            termo = p.replace(g, "").strip()
            break

    if not termo:
        m = re.search(r"(presidente|governador|ministro|prefeito)\s+(da|do|dos|das)\s+(.+)", p)
        if m:
            cargo = m.group(1).strip()
            local = m.group(3).strip()
            termo = f"{cargo} {local}"

    if not termo and "capital" in p:
        termo = p

    if not termo:
        return []

    try:
        sessao = criar_sessao_http()
        url = (
            "https://pt.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={quote_plus(termo)}&format=json"
        )
        resp = sessao.get(url, timeout=TIMEOUT_PADRAO)
        resp.raise_for_status()
        data = resp.json()

        itens = data.get("query", {}).get("search", [])
        resultados = []

        for item in itens[:4]:
            titulo = item.get("title", "")
            snippet = BeautifulSoup(item.get("snippet", ""), "html.parser").get_text(" ", strip=True)
            page_url = "https://pt.wikipedia.org/wiki/" + quote_plus(titulo.replace(" ", "_"))

            resultados.append({
                "url": page_url,
                "trecho": normalizar_texto(snippet),
                "texto": normalizar_texto(snippet),
                "score": 5
            })

        return resultados
    except Exception:
        return []

def buscar_wikidata_rotulo(pergunta: str):
    p = texto_norm(pergunta)

    termos = []
    if "presidente da china" in p:
        termos = ["Presidente da República Popular da China"]
    elif "presidente do brasil" in p:
        termos = ["Presidente do Brasil"]
    elif "presidente dos estados unidos" in p:
        termos = ["Presidente dos Estados Unidos"]

    if not termos:
        return []

    resultados = []
    try:
        sessao = criar_sessao_http()
        for termo in termos:
            url = (
                "https://www.wikidata.org/w/api.php"
                f"?action=wbsearchentities&search={quote_plus(termo)}&language=pt&format=json"
            )
            resp = sessao.get(url, timeout=TIMEOUT_PADRAO)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("search", [])[:2]:
                label = item.get("label", "")
                desc = item.get("description", "")
                concept = item.get("concepturi", "")
                resultados.append({
                    "url": concept,
                    "trecho": normalizar_texto(f"{label}. {desc}"),
                    "texto": normalizar_texto(f"{label}. {desc}"),
                    "score": 4
                })
    except Exception:
        return []

    return resultados

def buscar_na_internet(pergunta: str, max_links: int = TOP_LINKS_WEB):
    resultados = []

    wiki = buscar_wikipedia_direto(pergunta)
    if wiki:
        resultados.extend(wiki)

    wikidata = buscar_wikidata_rotulo(pergunta)
    if wikidata:
        resultados.extend(wikidata)

    links = pesquisar_links_web_multicamadas(pergunta, max_links=max_links * 3)

    for url in links:
        texto = extrair_texto_url(url)
        if not texto or len(texto) < MIN_TEXTO_WEB:
            continue

        trecho = gerar_trecho_relevante(texto, pergunta)
        score = score_resultado_web(trecho, pergunta, url)

        resultados.append({
            "url": url,
            "trecho": trecho,
            "texto": texto,
            "score": score
        })

    unicos = []
    vistos = set()
    for r in resultados:
        if r["url"] not in vistos:
            vistos.add(r["url"])
            unicos.append(r)

    unicos.sort(key=lambda x: x["score"], reverse=True)
    return unicos[:max_links]

def web_suficiente(resultados_web: list) -> bool:
    if not resultados_web:
        return False
    melhor_score = max(r.get("score", 0) for r in resultados_web)
    return melhor_score >= SCORE_MINIMO_WEB

def extrair_resposta_curta_web(pergunta: str, resultados_web: list) -> str:
    if not resultados_web:
        return ""

    pergunta_n = texto_norm(pergunta)

    padroes_nome = [
        r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+){1,4})"
    ]

    for item in resultados_web[:4]:
        trecho = item.get("trecho", "")
        if not trecho:
            continue

        if "presidente" in pergunta_n:
            for padrao in padroes_nome:
                nomes = re.findall(padrao, trecho)
                nomes_filtrados = []
                for nome in nomes:
                    nome_limpo = normalizar_texto(nome)
                    if len(nome_limpo.split()) >= 2:
                        if nome_limpo.lower() not in {"república popular", "estados unidos"}:
                            nomes_filtrados.append(nome_limpo)
                if nomes_filtrados:
                    return nomes_filtrados[0]

        if "capital" in pergunta_n:
            for padrao in padroes_nome:
                nomes = re.findall(padrao, trecho)
                if nomes:
                    return normalizar_texto(nomes[0])

    return ""

def montar_resposta_web_direta(resultados_web: list, pergunta: str, houve_base_local: bool = False):
    if not resultados_web:
        return (
            "Não localizei base suficiente para responder com segurança.\n\n"
            "OBSERVAÇÃO TÉCNICA:\n"
            "A pesquisa web não retornou fonte utilizável."
        )

    melhor = resultados_web[0]
    resposta_curta = extrair_resposta_curta_web(pergunta, resultados_web)
    trecho = limitar_texto(melhor.get("trecho", ""), 1000)
    url = melhor.get("url", "")

    linhas = []
    linhas.append("RESPOSTA DIRETA:")
    if resposta_curta:
        linhas.append(f"Indício principal localizado: {resposta_curta}.\n")
    else:
        linhas.append("Localizei fonte web com indício relevante para responder à pergunta.\n")

    linhas.append("FUNDAMENTO:")
    linhas.append(f"Fonte principal: {url}")
    linhas.append(f"Trecho relevante: {trecho}\n")
    linhas.append("GRAU DE CERTEZA:")
    linhas.append("Pesquisa web suficiente para resposta preliminar; recomenda-se conferência na fonte.\n")
    linhas.append("OBSERVAÇÃO TÉCNICA:")
    obs = "Resposta montada por regras, sem uso de provedor de IA."
    if houve_base_local:
        obs += " A base local foi consultada, mas a internet se mostrou mais útil para esta pergunta."
    linhas.append(obs)

    return "\n".join(linhas)

# =========================================================
# ROTEAMENTO
# =========================================================
def classificar_rota(pergunta: str) -> str:
    if pergunta_pede_identidade(pergunta):
        return "sistema"

    if resposta_data_hora_local(pergunta):
        return "sistema"

    ref = detectar_referencia(pergunta)

    if pergunta_tecnica_da_base(pergunta) or ref["tipo"] in {"it", "decreto"}:
        return "base_primeiro"

    return "web_primeiro"

def decidir_origem_resposta(pergunta: str, trechos_base: list, resultados_web: list, ref: dict, rota: str):
    base_ok = base_local_suficiente(trechos_base, pergunta, ref)
    web_ok = web_suficiente(resultados_web)
    tecnica = pergunta_tecnica_da_base(pergunta)

    if rota == "web_primeiro":
        if web_ok:
            return "web_direta"
        if base_ok:
            return "base_local"
        return "nenhuma"

    if rota == "base_primeiro":
        if base_ok and web_ok:
            if tecnica or ref["tipo"] in {"it", "decreto"}:
                return "base_com_apoio_web"
            return "web_direta"
        if base_ok:
            return "base_local"
        if web_ok:
            return "web_direta"
        return "nenhuma"

    return "nenhuma"

# =========================================================
# GERAÇÃO DE RESPOSTA
# =========================================================
def gerar_resposta(pergunta: str, modo_estrito: bool = False, pesquisar_web: bool = True):
    inicio = time.time()

    if modo_estrito:
        pesquisar_web = False

    try:
        resposta_id = resposta_identidade(pergunta)
        if resposta_id:
            tempo = round(time.time() - inicio, 2)
            return {
                "ok": True,
                "texto": resposta_id,
                "tempo": tempo,
                "trechos": [],
                "erro": "",
                "origem": "sistema",
                "fontes_web": [],
                "resultados_web": [],
                "docs_candidatos": [],
                "ref_detectada": {},
                "rota": "sistema"
            }

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
                "fontes_web": [],
                "resultados_web": [],
                "docs_candidatos": [],
                "ref_detectada": {},
                "rota": "sistema"
            }

        rota = classificar_rota(pergunta)

        trechos = []
        docs_candidatos = []
        ref = detectar_referencia(pergunta)
        resultados_web = []

        if rota == "web_primeiro":
            if pesquisar_web:
                resultados_web = buscar_na_internet(pergunta, max_links=TOP_LINKS_WEB)

            if not web_suficiente(resultados_web):
                trechos = []
                docs_candidatos = []

        else:
            trechos, docs_candidatos, ref = buscar_trechos_na_base(pergunta, TOP_CHUNKS)
            if pesquisar_web:
                resultados_web = buscar_na_internet(pergunta, max_links=TOP_LINKS_WEB)

        origem = decidir_origem_resposta(pergunta, trechos, resultados_web, ref, rota)

        if origem == "base_local":
            texto = montar_resposta_base_local_direta(pergunta, trechos, houve_apoio_web=False)
        elif origem == "base_com_apoio_web":
            texto = montar_resposta_base_local_direta(pergunta, trechos, houve_apoio_web=True)
        elif origem == "web_direta":
            texto = montar_resposta_web_direta(
                resultados_web,
                pergunta,
                houve_base_local=bool(trechos)
            )
        else:
            if modo_estrito:
                texto = "Não localizei base suficiente para responder com segurança."
            else:
                texto = (
                    "Não localizei base suficiente para responder com segurança.\n\n"
                    "OBSERVAÇÃO TÉCNICA:\n"
                    "Após consultar a base local e múltiplas fontes web, não localizei fundamento suficiente para responder com segurança."
                )

        tempo = round(time.time() - inicio, 2)
        return {
            "ok": True,
            "texto": texto,
            "tempo": tempo,
            "trechos": trechos,
            "erro": "",
            "origem": origem,
            "fontes_web": [r["url"] for r in resultados_web],
            "resultados_web": resultados_web,
            "docs_candidatos": docs_candidatos,
            "ref_detectada": ref,
            "rota": rota
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
            "fontes_web": [],
            "resultados_web": [],
            "docs_candidatos": [],
            "ref_detectada": {},
            "rota": "erro"
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
        value=False
    )
    mostrar_debug = st.checkbox(
        "Mostrar diagnóstico técnico",
        value=True
    )
    pesquisar_web = st.checkbox(
        "Pesquisar automaticamente na internet além da base local",
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
if st.button("INICIAR"):
    if not pergunta.strip():
        st.warning("Digite uma pergunta.")
    else:
        with st.spinner("ROMANUS consultando..."):
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
                for fonte in resultado["fontes_web"][:5]:
                    st.markdown(
                        f'<div class="fonte-box"><a href="{escape_html(fonte)}" target="_blank">{escape_html(fonte)}</a></div>',
                        unsafe_allow_html=True
                    )

        if mostrar_debug:
            base_total = carregar_base_local()
            indice_total = indexar_base_em_chunks()
            arquivos_usados = [t["arquivo"] for t in resultado.get("trechos", [])]
            referencias = [t["referencia"] for t in resultado.get("trechos", []) if t.get("referencia")]
            docs_candidatos = [d["arquivo"] for d in resultado.get("docs_candidatos", [])]
            ref = resultado.get("ref_detectada", {})

            melhor_score_base = 0
            if resultado.get("trechos"):
                melhor_score_base = max(t.get("score", 0) for t in resultado["trechos"])

            melhor_score_web = 0
            if resultado.get("resultados_web"):
                melhor_score_web = max(r.get("score", 0) for r in resultado["resultados_web"])

            debug_texto = (
                f"Rota escolhida: {resultado.get('rota', 'desconhecida')}\n"
                f"Arquivos na base: {len(base_total)}\n"
                f"Chunks totais indexados: {len(indice_total)}\n"
                f"Documentos candidatos: {docs_candidatos if docs_candidatos else 'Nenhum'}\n"
                f"Trechos retornados da base: {len(resultado.get('trechos', []))}\n"
                f"Resultados web: {len(resultado.get('resultados_web', []))}\n"
                f"Arquivos usados: {arquivos_usados if arquivos_usados else 'Nenhum'}\n"
                f"Referências localizadas: {referencias if referencias else 'Nenhuma'}\n"
                f"Referência detectada: {ref if ref else 'Nenhuma'}\n"
                f"Melhor score da base: {melhor_score_base}\n"
                f"Score mínimo da base: {SCORE_MINIMO_BASE}\n"
                f"Melhor score web: {melhor_score_web}\n"
                f"Score mínimo web: {SCORE_MINIMO_WEB}\n"
                f"Tempo de resposta: {resultado.get('tempo', 0)} s\n"
                f"Modo estrito: {'Ligado' if modo_estrito else 'Desligado'}\n"
                f"Pesquisa web automática: {'Ligada' if pesquisar_web else 'Desligada'}\n"
                f"Pergunta técnica da base: {'Sim' if pergunta_tecnica_da_base(pergunta) else 'Não'}\n"
                f"Pergunta geral web: {'Sim' if pergunta_geral_web(pergunta) else 'Não'}\n"
                f"Pergunta pede objeto da norma: {'Sim' if pergunta_pede_objeto_norma(pergunta) else 'Não'}\n"
                f"Origem final da resposta: {resultado.get('origem', 'desconhecida')}"
            )

            st.markdown("### Diagnóstico")
            st.markdown(
                f'<div class="debug-box">{escape_html(debug_texto)}</div>',
                unsafe_allow_html=True
            )
