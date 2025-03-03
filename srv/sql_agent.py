import os
import sys
import getpass
import json
import re  # Para remover blocos ```sql ... ```
from langchain_community.utilities import SQLDatabase
from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate

# Desativar LangSmith e evitar conexões desnecessárias
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Obter API Key da Groq
if not os.environ.get("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = getpass.getpass("Enter API key for Groq: ")

# Inicializar LLM
llm = init_chat_model("llama3-8b-8192", model_provider="groq")

# Conectar ao SQLite
db = SQLDatabase.from_uri("sqlite:///db.sqlite")

def get_table_info():
    """Obter a estrutura de todas as tabelas disponíveis no banco de dados."""
    tables = db.get_usable_table_names()
    if not tables:
        raise ValueError("Nenhuma tabela encontrada!")

    # Obter estrutura das tabelas
    table_info = {
        table: db.get_table_info([table]) 
        for table in tables
    }
    return table_info

# Prompt otimizado para geração da query SQL
query_prompt_template = PromptTemplate(
    input_variables=["table_info", "input"],
    template=(
        "Gera uma query SQL válida baseada na estrutura da base de dados SQLite abaixo.\n\n"
        "** Estrutura da Base de Dados:**\n{table_info}\n\n"
        "**Pergunta:** {input}\n\n"
        "**Importante:**\n"
        "- Para comparações de status, usa `LOWER(status) = 'aprovado'` para evitar problemas de maiúsculas/minúsculas.\n"
        "- NÃO uses `information_schema.tables`, pois SQLite não o suporta.\n"
        "- Retorna **apenas a query SQL pura, sem formatação ou explicações**.\n"
    ),
)

# Função para limpar a query gerada
def clean_query(query):
    """Remove formatação extra da query SQL gerada pelo LLM."""
    query = re.sub(r"```sql\s*([\s\S]*?)\s*```", r"\1", query)  # Remove blocos ```sql ... ```
    query = query.strip()  # Remove espaços desnecessários
    return query

# Gerar a query SQL
def write_query(question):
    """Gerar uma query SQL compatível com SQLite."""
    table_info = get_table_info()
    prompt = query_prompt_template.format(
        table_info=table_info,
        input=question
    )
    
    response = llm.invoke(prompt)
    raw_query = response.content if hasattr(response, "content") else response
    return clean_query(raw_query)  # Limpar a query antes de retornar

# Executar a query diretamente no SQLite
def execute_query(query):
    """Executar a query SQL no SQLite."""
    try:
        result = db.run(query)
        return {"result": result}
    except Exception as e:
        raise ValueError(f"Erro ao executar a query SQL: {str(e)}")

# Gerar resposta baseada no resultado da query
def generate_answer(question, query, result):
    prompt = f"Pergunta: {question}\nQuery SQL: {query}\nResultado SQL: {result}\n\nGera uma resposta coerente."
    return llm.invoke(prompt).content

# Execução direta (para integração com Node.js via subprocess)
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERRO: Nenhuma pergunta fornecida.", file=sys.stderr)
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    
    try:
        query = write_query(question)
        result = execute_query(query)
        answer = generate_answer(question, query, result)
        print(answer)
    except Exception as e:
        print(f"Erro: {str(e)}", file=sys.stderr)
        sys.exit(1)
