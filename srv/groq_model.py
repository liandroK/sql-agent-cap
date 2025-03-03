import os
import dotenv
from langchain.chat_models import init_chat_model
import sys

# Carregar variáveis do .env
dotenv.load_dotenv()

# Obter a API Key da Groq
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("ERRO: A API Key da Groq não está definida no .env!", file=sys.stderr)
    sys.exit(1)

# Inicializar o modelo Llama 3-8B
llm = init_chat_model("llama3-8b-8192", model_provider="groq")

# Função para gerar resposta
def ask_groq(question):
    response = llm.invoke(question)
    return response.content.strip()

# Se o script for chamado via terminal
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERRO: Nenhuma pergunta fornecida.", file=sys.stderr)
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    resposta = ask_groq(question)

    print(resposta)  # Importante: imprimir a resposta para que o Node.js capture!
