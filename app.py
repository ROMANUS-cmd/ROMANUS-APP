import streamlit as st
from google import genai
from PIL import Image
import os
import re
from pypdf import PdfReader

# =========================================
# CONFIGURAÇÃO INICIAL
# =========================================
st.set_page_config(page_title="ROMANUS", layout="wide")

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

BASE_CONHECIMENTO_DIR = "base_conhecimento"

# =========================================
# PROMPT PRINCIPAL DA ROMANUS
# =========================================
PROMPT_SISTEMA = """
Você é ROMANUS, uma inteligência artificial técnica, objetiva e confiável.

IDENTIDADE
Seu nome é ROMANUS.
Seu posicionamento é: "A IA que não passa pano."
Seu papel é fornecer respostas diretas, técnicas, jurídicas, administrativas e operacionais, com máxima precisão e sem floreios.
Seu estilo deve ser firme, claro, profissional, disciplinado e eficiente.
Você pode usar sarcasmo leve e inteligente apenas quando couber, sem comprometer a precisão técnica.

MISSÃO
Sua missão é responder com base:
1. na base de conhecimento local fornecida pelo sistema;
2. no conteúdo documental encontrado;
3. em conhecimento complementar do modelo apenas quando a base local for insuficiente e o sistema permitir.

Você deve priorizar:
- exatidão;
- fidelidade ao texto localizado;
- utilidade prática;
- clareza operacional;
- honestidade sobre limites.

REGRAS ABSOLUTAS
1. Nunca invente leis, artigos, incisos, itens, subitens, datas, normas, entendimentos, citações ou fatos.
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
1. primeiro, analisar o conteúdo da base local fornecida no contexto;
2. segundo, responder com base nessa base;
3. terceiro, apenas complementar com conhecimento geral se o sistema permitir e sem contradizer a base;
4. se não for possível responder com segurança, informar a limitação.

COMO USAR A BASE LOCAL
Se o sistema fornecer trechos de documentos, normas, leis, instruções, manuais ou arquivos:
- trate isso como a fonte principal;
- responda com fidelidade ao conteúdo;
- cite o nome do arquivo, norma ou documento, se estiver disponível;
- cite artigo, item, subitem, capítulo ou seção, se estiver disponível;
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
- tom emocional excessivo;
- linguagem de vendedor;
- falsa segurança.

ESTRUTURA PADRÃO DE RESPOSTA
Quando a pergunta exigir fundamentação, use:

RESPOSTA DIRETA:
[resposta objetiva]

FUNDAMENTO:
[nome do documento / norma / arquivo]
[artigo / item / subitem / capítulo / seção, se disponível]

OBSERVAÇÃO TÉCNICA:
[apenas se necessário]

Se a pergunta for simples, responda de forma simples, sem enfeitar.

CONDUTA EM PERGUNTAS JURÍDICAS E NORMATIVAS
Quando a pergunta envolver lei, decreto, regulamento, norma ou instrução:
- responda apenas com o que puder sustentar;
- cite fundamento sempre que possível;
- diferencie texto da norma e interpretação;
- nunca invente artigo;
- nunca use tom categórico sem base.

CONDUTA EM PERGUNTAS OPERACIONAIS
Quando a pergunta for prática:
1. diga o que é;
2. diga o que deve ser feito;
3. diga com base em quê;
4. diga o risco do erro, se relevante.

CONDUTA EM RESUMOS
Quando for pedido resumo:
- preserve o sentido técnico;
- destaque exigências, proibições, exceções, condições e efeitos;
- foque no que obriga, permite, limita ou beneficia.

CONDUTA EM REDAÇÃO TÉCNICA
Quando o usuário pedir ofício, parecer, requerimento, despacho, mensagem ou texto técnico:
- redija em linguagem formal e profissional;
- mantenha coerência administrativa;
- não invente fundamento;
- se faltar base, use redação prudente e neutra.

TONALIDADE
A ROMANUS deve transmitir:
- autoridade técnica;
- objetividade;
- confiabilidade;
- disciplina;
- clareza.

Sarcasmo só é permitido de forma breve, elegante e controlada.
Nunca use sarcasmo em temas sensíveis, jurídicos delicados, saúde, segurança, acidentes, morte ou sofrimento pessoal.

PROIBIÇÕES
É proibido:
- criar citações falsas;
- criar jurisprudência falsa;
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
"""

# =========================================
# FUNÇÕES DE LEITURA DA BASE LOCAL
# =========================================
def extrair_texto_pdf(caminho_pdf):
    texto = []
    try:
        reader = PdfReader(caminho_pdf)
        for pagina in reader.pages:
            conteudo = pagina.extract_text()
            if conteudo:
                texto.append(conteudo)
    except Exception:
        return ""
    return "\n".join(texto)

def carregar_base_local():
    base = []

    if not os.path.exists(BASE_CONHECIMENTO_DIR):
        return base

    for raiz, _, arquivos in os.walk(BASE_CONHECIMENTO_DIR):
        for arquivo in arquivos:
            caminho = os.path.join(raiz, arquivo)
            nome_arquivo = os.path.relpath(caminho, BASE_CONHECIMENTO_DIR)

            texto = ""

            try:
                if arquivo.lower().endswith(".txt"):
                    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                        texto = f.read()

                elif arquivo.lower().endswith(".pdf"):
                    texto = extrair_texto_pdf(caminho)

                if texto and texto.strip():
                    base.append({
                        "arquivo": nome_arquivo,
                        "texto": texto,
                        "texto_lower": texto.lower()
                    })

            except Exception:
                continue

    return base

def buscar_na_base(pergunta, top_k=3):
    base = carregar_base_local()
    pergunta_lower = pergunta.lower().strip()

    palavras_ignoradas = {
        "oi", "ola", "olá", "bom", "boa", "dia", "tarde", "noite",
        "obrigado", "obrigada", "valeu", "ok", "certo", "entendi",
        "por", "para", "com", "sem", "sobre", "isso", "essa", "esse",
        "qual", "quais", "como", "onde", "quando"
    }

    termos = [
        t for t in re.findall(r"\w+", pergunta_lower)
        if len(t) >= 3 and t not in palavras_ignoradas
    ]

    if not termos:
        return []

    resultados = []

    for item in base:
        score = 0
        texto_lower = item["texto_lower"]
        nome_lower = item["arquivo"].lower()

        for termo in termos:
            score += nome_lower.count(termo) * 15
            score += texto_lower.count(termo) * 3

        if pergunta_lower in texto_lower:
            score += 100

        if score > 0:
            resultados.append({
                "arquivo": item["arquivo"],
                "texto": item["texto"],
                "score": score
            })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:top_k]

def montar_contexto_base(resultados):
    if not resultados:
        return "Nenhum conteúdo relevante foi localizado na base local."

    partes = []
    for i, item in enumerate(resultados, start=1):
        trecho = item["texto"][:4000]
        partes.append(
            f"[DOCUMENTO {i}]\\n"
            f"Arquivo: {item['arquivo']}\\n"
            f"Conteúdo localizado:\\n{trecho}"
        )

    return "\\n\\n".join(partes)

# =========================================
# GERAÇÃO DE RESPOSTA
# =========================================
def gerar_resposta(pergunta):
    resultados_base = buscar_na_base(pergunta, top_k=3)
    contexto_base = montar_contexto_base(resultados_base)

    prompt_final = f"""
{PROMPT_SISTEMA}

PERGUNTA DO USUÁRIO:
{pergunta}

BASE LOCAL LOCALIZADA:
{contexto_base}

INSTRUÇÕES FINAIS DE EXECUÇÃO
1. Priorize integralmente a base local acima.
2. Se houver resposta suficiente na base, responda com base nela.
3. Cite o nome do arquivo consultado sempre que possível.
4. Não invente artigo, item, fundamento ou trecho.
5. Se a base for insuficiente, diga isso claramente.
6. Só complemente com conhecimento geral se isso não contrariar a base e se for realmente necessário.
7. Se não houver segurança, admita a limitação.
"""

    try:
        resposta = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt_final
        )
        return resposta.text.strip()

    except Exception as e:
        return f"Erro ao gerar resposta: {str(e)}"

# =========================================
# INTERFACE
# =========================================
st.markdown("""
<style>
[data-testid="stHeader"] {
    background: transparent;
}

.main .block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
    max-width: 1100px;
}

.romanus-title {
    text-align: center;
    font-size: 42px;
    font-weight: 900;
    margin-bottom: 0;
}

.romanus-subtitle {
    text-align: center;
    font-size: 18px;
    margin-top: 0;
    margin-bottom: 20px;
    opacity: 0.85;
}

.romanus-slogan {
    text-align: center;
    font-size: 15px;
    margin-top: 10px;
    margin-bottom: 30px;
    opacity: 0.8;
}
</style>
""", unsafe_allow_html=True)

# =========================================
# TOPO
# =========================================
imagem_path = "assets/gladiador.png"

if os.path.exists(imagem_path):
    imagem = Image.open(imagem_path)
    st.image(imagem, width=220)

st.markdown('<div class="romanus-title">ROMANUS</div>', unsafe_allow_html=True)
st.markdown('<div class="romanus-subtitle">A IA que não passa pano.</div>', unsafe_allow_html=True)
st.markdown('<div class="romanus-slogan">Respostas diretas. Soluções reais.</div>', unsafe_allow_html=True)

# =========================================
# ENTRADA DO USUÁRIO
# =========================================
pergunta = st.text_area("Digite sua ordem:", height=120, placeholder="O que você precisa resolver hoje?")

if st.button("INICIAR"):
    if not pergunta.strip():
        st.warning("Digite uma pergunta.")
    else:
        with st.spinner("ROMANUS analisando a base..."):
            resposta = gerar_resposta(pergunta)

        st.markdown("### Resposta")
        st.write(resposta)
