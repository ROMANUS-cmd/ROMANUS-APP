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
