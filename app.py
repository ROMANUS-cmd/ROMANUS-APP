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
MODELO_GEMINI = "gemini-2.5-flash"
TOP_K = 5
JANELA_TRECHO = 2600

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

MISSÃO
Sua missão é responder prioritariamente com base na base local fornecida pelo sistema, com fidelidade documental e rigor técnico.
Você deve buscar a fonte mais central, mais direta e mais específica para responder à pergunta.
Você não deve responder com base em menções periféricas quando houver indício de que existe documento mais adequado.

REGRAS ABSOLUTAS
1. Nunca invente leis, artigos, itens, subitens, datas, normas, entendimentos, citações ou fatos.
2. Nunca afirme que encontrou algo se isso não constar de forma real na base recebida.
3. Nunca trate hipótese como fato.
4. Nunca complete lacunas com suposição disfarçada de certeza.
5. Nunca distorça o conteúdo localizado.
6. Se não houver base suficiente, diga isso claramente.
7. Se houver dúvida relevante, deixe a incerteza explícita.
8. Sempre prefira precisão a velocidade.
9. Sempre prefira resposta exata a texto longo e genérico.
10. Sempre responda em português do Brasil.

HIERARQUIA DE QUALIDADE DA FONTE
Ao analisar a base, siga esta ordem de preferência:
1. documento que define expressamente o conceito perguntado;
2. documento que liste expressamente os requisitos, medidas, itens ou critérios perguntados;
3. documento técnico específico do tema;
4. norma geral relacionada;
5. documento administrativo, procedimental, formulário, anexo de referência, índice, sumário ou menção lateral.

REGRA DE PRIORIDADE DOCUMENTAL
Se a pergunta pedir definição, lista, requisitos, medidas, critérios ou classificação:
- priorize o documento que traga isso expressamente;
- não use como fundamento principal um trecho que apenas menciona o tema;
- não use sumário, índice, anexo citado sem conteúdo, nota lateral ou referência indireta como base principal;
- não trate menção genérica como resposta suficiente;
- se houver apenas menção indireta, diga claramente que a base não trouxe a definição/lista expressa.

USO DA BASE LOCAL
Se o sistema fornecer trechos de documentos:
- trate isso como fonte principal;
- responda com fidelidade ao conteúdo;
- cite o nome do arquivo, se disponível;
- diferencie claramente:
  a) texto expresso;
  b) resumo fiel;
  c) interpretação mínima.

QUANDO HOUVER TEXTO EXPRESSO
Se a base trouxer resposta clara e direta:
- responda de forma objetiva;
- preserve o sentido original;
- não acrescente requisito inexistente;
- não amplie o texto além do que ele sustenta.

QUANDO A BASE FOR PARCIAL
Se a base trouxer apenas elementos relacionados:
- diga expressamente que não há resposta literal completa;
- apresente apenas conclusão parcial;
- identifique que se trata de interpretação mínima;
- não extrapole além do que o texto sustenta;
- não transforme referência lateral em fundamento principal.

QUANDO HOUVER CONFLITO ENTRE TRECHOS
Se houver mais de um trecho:
- prefira o mais específico;
- prefira o mais central ao tema;
- prefira o que contenha definição, lista, regra ou critério expresso;
- descarte trechos meramente incidentais como fundamento principal.

FRASES OBRIGATÓRIAS QUANDO NECESSÁRIO
Use estas fórmulas quando forem verdadeiras:
- "Não localizei base suficiente para responder com segurança."
- "A base consultada não trouxe resposta literal para esse ponto."
- "O texto localizado permite apenas conclusão parcial."
- "Não é possível confirmar isso sem extrapolar a base."
- "Não encontrei elemento suficiente para responder com precisão."
- "Os trechos localizados apenas mencionam o tema, mas não trazem a definição/lista expressa."

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
- "depende" sem explicar do que depende;
- enrolação;
- falsa segurança;
- usar referência periférica como se fosse fundamento principal.

ESTRUTURA PADRÃO
Quando houver base útil, use preferencialmente:

RESPOSTA DIRETA:
[resposta objetiva]

FUNDAMENTO:
[arquivo consultado e artigo/item se localizados]

GRAU DE CERTEZA:
[expresso na base / conclusão parcial / insuficiente]

OBSERVAÇÃO TÉCNICA:
[apenas se necessário]

CONDUTA EM PERGUNTAS JURÍDICAS E NORMATIVAS
- responda apenas com o que puder sustentar;
- cite fundamento sempre que possível;
- diferencie texto localizado de interpretação;
- nunca invente artigo;
- nunca use tom categórico sem base;
- quando a pergunta pedir um rol, uma lista ou uma definição, só afirme isso se o rol, a lista ou a definição estiver expressamente localizado.

INSTRUÇÃO ESPECIAL PARA ENUMERAÇÕES
Se a pergunta pedir lista, rol, definição ou enumeração:
- procure no trecho localizado expressões como:
  "constituem", "são", "compreendem", "incluem", "fica instituído", "deverá ser levado em consideração", "classificam-se", "são medidas", "são requisitos";
- se houver enumeração expressa, reproduza a lista fielmente;
- se houver incisos, preserve a estrutura;
- se não houver enumeração expressa, não invente a lista.

PROIBIÇÕES
É proibido:
- criar citações falsas;
- fingir pesquisa;
- omitir incerteza;
- esconder falta de base com texto bonito;
- contradizer a base local sem explicar;
- responder como se tivesse certeza quando não tem;
- usar índice, sumário, título de anexo ou menção indireta como se fossem conteúdo normativo completo.

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
# CLIENTE GEMINI
# =========================================================
@st.cache_resource
def criar_cliente():
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("A chave GEMINI_API_KEY não foi encontrada no secrets.")
    return genai.Client(api_key=api_key)

# =========================================================
# LEITURA DE ARQUIVOS
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
# APOIO DE BUSCA
# =========================================================
PALAVRAS_IGNORADAS = {
    "a", "o", "e", "de", "da", "do", "das", "dos", "um", "uma",
    "em", "por", "para", "com", "sem", "que", "como", "qual",
    "quais", "onde", "quando", "isso", "essa", "esse", "sobre",
    "bom", "boa", "dia", "tarde", "noite", "oi", "ola", "olá",
    "as", "os", "ao", "aos", "na", "no", "nas", "nos"
}

def normalizar_termos(texto: str):
    return [
        t for t in re.findall(r"\w+", (texto or "").lower())
        if len(t) >= 3 and t not in PALAVRAS_IGNORADAS
    ]

def pergunta_pede_lista(pergunta: str) -> bool:
    p = (pergunta or "").lower()
    gatilhos = [
        "quais", "lista", "rol", "enumere", "enumeração",
        "medidas", "requisitos", "itens", "critérios",
        "quais são", "quais as", "defina", "definição"
    ]
    return any(g in p for g in gatilhos)

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
            score += 20

    if pergunta_pede_lista(pergunta):
        for palavra in ["anexo", "quadro", "tabela", "medidas", "regulamento", "decreto"]:
            if palavra in nome_lower:
                score += 18

    return score

def localizar_melhor_posicao(texto: str, pergunta: str) -> int:
    texto_lower = (texto or "").lower()
    termos = normalizar_termos(pergunta)

    if not termos:
        return 0

    posicoes = []

    for termo in termos:
        pos = texto_lower.find(termo)
        if pos != -1:
            posicoes.append(pos)

    if posicoes:
        return min(posicoes)

    padroes_fortes = [
        "constituem", "são medidas", "medidas de segurança contra incêndio",
        "capítulo", "artigo", "art.", "incluem", "compreendem"
    ]

    for padrao in padroes_fortes:
        pos = texto_lower.find(padrao)
        if pos != -1:
            return pos

    return 0

def extrair_trecho_relevante(texto: str, pergunta: str, janela: int = JANELA_TRECHO) -> str:
    texto_limpo = texto or ""
    if not texto_limpo.strip():
        return ""

    pos = localizar_melhor_posicao(texto_limpo, pergunta)
    inicio = max(0, pos - 700)
    fim = min(len(texto_limpo), pos + janela)

    return texto_limpo[inicio:fim].strip()

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

# =========================================================
# BUSCA NA BASE
# =========================================================
def buscar_na_base(pergunta: str, top_k: int = TOP_K):
    base = carregar_base_local()
    if not base:
        return []

    termos = normalizar_termos(pergunta)
    resultados = []

    for item in base:
        nome = item["arquivo"].lower()
        texto = item["texto_lower"]
        score = 0

        for termo in termos:
            score += nome.count(termo) * 30
            score += texto.count(termo) * 4

        if pergunta.lower().strip() and pergunta.lower().strip() in texto:
            score += 120

        score += score_nome_arquivo(item["arquivo"], pergunta)

        if pergunta_pede_lista(pergunta):
            gatilhos_lista = [
                "constituem", "incluem", "compreendem", "são medidas",
                "medidas de segurança", "deverá ser levado em consideração",
                "i -", "ii -", "iii -", "iv -"
            ]
            for g in gatilhos_lista:
                if g in texto:
                    score += 22

        if "decreto" in pergunta.lower() and "decreto" in nome:
            score += 50

        if score > 0:
            trecho = extrair_trecho_relevante(item["texto"], pergunta, janela=JANELA_TRECHO)
            referencia = extrair_referencia_local(trecho)

            resultados.append({
                "arquivo": item["arquivo"],
                "texto": item["texto"],
                "trecho": trecho,
                "score": score,
                "referencia": referencia
            })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:top_k]

def montar_contexto(resultados, pergunta: str):
    if not resultados:
        return "Nenhum conteúdo relevante foi localizado na base local."

    blocos = []
    for i, item in enumerate(resultados, start=1):
        bloco = (
            f"[DOCUMENTO {i}]\n"
            f"ARQUIVO: {item['arquivo']}\n"
            f"REFERÊNCIA LOCALIZADA: {item['referencia'] if item['referencia'] else 'não localizada'}\n"
            f"TRECHO RELEVANTE:\n{item['trecho']}\n"
        )
        blocos.append(bloco)

    instrucao_pergunta = ""
    if pergunta_pede_lista(pergunta):
        instrucao_pergunta = (
            "\n[ATENÇÃO ESPECIAL]\n"
            "A pergunta do usuário pede lista, enumeração, rol ou medidas. "
            "Procure por enumeração expressa no trecho e reproduza fielmente.\n"
        )

    return instrucao_pergunta + "\n\n".join(blocos)

# =========================================================
# GERAÇÃO DE RESPOSTA
# =========================================================
def gerar_resposta(pergunta: str, modo_estrito: bool = True):
    cliente = criar_cliente()
    resultados = buscar_na_base(pergunta, TOP_K)
    contexto = montar_contexto(resultados, pergunta)

    prompt_final = f"""
{PROMPT_SISTEMA}

PERGUNTA DO USUÁRIO:
{pergunta}

BASE LOCAL LOCALIZADA:
{contexto}

INSTRUÇÕES FINAIS DE EXECUÇÃO
1. Priorize integralmente a base local.
2. Se a base responder, responda com base nela.
3. Cite os arquivos usados e a referência localizada, se houver.
4. Não invente fundamento.
5. Se a pergunta pedir lista, rol, enumeração, medidas ou requisitos, só apresente a lista se ela estiver expressamente visível no trecho.
6. Se houver enumeração expressa, reproduza a enumeração fielmente.
7. Se os trechos apenas mencionarem o tema, diga isso claramente.
8. Não esconda limitação com texto bonito.
9. Não use sumário, índice ou menção indireta como fundamento principal.
10. Se houver um trecho mais específico que outro, prefira o mais específico.

Se não houver base suficiente, use uma das fórmulas de insuficiência previstas no prompt.
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

        if modo_estrito and not resultados:
            texto = "Não localizei base suficiente para responder com segurança."

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
        with st.spinner("ROMANUS analisando a base..."):
            resultado = gerar_resposta(pergunta, modo_estrito=modo_estrito)

        if not resultado["ok"]:
            st.error("Erro ao gerar resposta.")
            st.code(resultado["erro"])
        else:
            st.markdown("### Resposta")
            st.markdown(
                f'<div class="bloco-resposta">{resultado["texto"]}</div>',
                unsafe_allow_html=True
            )

        if mostrar_debug:
            arquivos_usados = [r["arquivo"] for r in resultado.get("resultados", [])]
            referencias = [r["referencia"] for r in resultado.get("resultados", []) if r.get("referencia")]
            base_total = carregar_base_local()

            debug_texto = (
                f"Arquivos na base: {len(base_total)}\n"
                f"Arquivos usados na busca: {len(arquivos_usados)}\n"
                f"Lista de arquivos usados: {arquivos_usados if arquivos_usados else 'Nenhum'}\n"
                f"Referências localizadas: {referencias if referencias else 'Nenhuma'}\n"
                f"Modelo: {MODELO_GEMINI}\n"
                f"Tempo de resposta: {resultado.get('tempo', 0)} s\n"
                f"Modo estrito: {'Ligado' if modo_estrito else 'Desligado'}"
            )

            st.markdown("### Diagnóstico")
            st.markdown(
                f'<div class="debug-box">{debug_texto}</div>',
                unsafe_allow_html=True
            )
