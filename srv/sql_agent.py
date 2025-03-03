import os
import sys
import getpass
import json
import re
from langchain_community.utilities import SQLDatabase
from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate

# Desativar LangSmith e evitar conexões desnecessárias
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Obter API Key para a Groq (caso necessário)
if not os.environ.get("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = getpass.getpass("Enter API key for Groq: ")

# Inicializar LLM
llm = init_chat_model("llama3-8b-8192", model_provider="groq")

# Conectar ao SQLite
db = SQLDatabase.from_uri("sqlite:///db.sqlite")

def get_table_info():
    tables = db.get_usable_table_names()
    if not tables:
        raise ValueError("Nenhuma tabela encontrada!")
    table_info = {
        table: db.get_table_info([table])
        for table in tables
    }
    return table_info



# Prompt base para gerar a query
query_prompt_template = PromptTemplate(
    input_variables=["table_info", "valor_total", "fornecedor_id"],
    template=(
        "Aqui estão as tabelas existentes e as colunas de cada uma:\n"
        "{table_info}\n\n"
        "Regras para a query SQL:\n"
        "- Apenas retornar ordens do MESMO fornecedor ({fornecedor_id}).\n"
        "- Apenas ordens com valor_total entre +/-20% de {valor_total}.\n"
        "- Fazer JOIN com my_orders_Fornecedor f ON o.fornecedor_ID = f.ID.\n"
        "- Selecionar também 'f.ativo'.\n"
        "- NÃO USAR f.nome! Usar f.name se for preciso o nome. Mas obrigatoriamente inclui 'f.ativo'.\n\n"
        "Retorna apenas a query SQL pura, sem formatações nem ```sql ...```.\n"
    ),
)

#Diminuir o nº de toekns de input
def clean_query(query):
    """Remove formatação extra (blocos ```sql ...```) da query gerada pelo LLM."""
    query = re.sub(r"```sql\s*([\s\S]*?)\s*```", r"\1", query)
    return query.strip()





def write_query(valor_total, fornecedor_id):
    table_info = get_table_info()
    prompt = query_prompt_template.format(
        table_info=table_info,
        valor_total=valor_total,
        fornecedor_id=fornecedor_id
    )
    # LOG 1: Mostrar o prompt enviado ao LLM
    print("==DEBUG== [write_query] Prompt para gerar query SQL:\n", prompt, "\n", flush=True)

    response = llm.invoke(prompt)
    raw_query = response.content if hasattr(response, "content") else response

    # LOG 2: Mostrar a query bruta antes de limpar
    print("==DEBUG== [write_query] Query bruta do LLM:\n", raw_query, "\n", flush=True)

    query = clean_query(raw_query)

    # LOG 3: Mostrar a query final
    print("==DEBUG== [write_query] Query final (limpa):\n", query, "\n", flush=True)
    return query


def execute_query(query):
    print(f"==DEBUG== [execute_query] Vou executar:\n{query}\n", flush=True)
    try:
        if "f.nome" in query:
            raise ValueError("ERRO: Query inválida! A coluna correta é 'f.name', não 'f.nome'.")
        
        result = db.run(query)
        print("==DEBUG== [execute_query] Resultado obtido:\n", result, "\n", flush=True)

        if not result or len(result) == 0:
            print("==ERRO== [execute_query] Nenhum dado retornado pela query!", flush=True)
            return []

        return result
    except Exception as e:
        print(f"==ERRO== [execute_query] Erro ao executar a query: {str(e)}", flush=True)
        return []




approval_prompt_template = PromptTemplate(
    input_variables=["valor_total", "fornecedor_id", "resultados"],
    template=(
        "Nova ordem: valor_total={valor_total}, fornecedor_id={fornecedor_id}.\n"
        "Resultados semelhantes (do mesmo fornecedor):\n{resultados}\n\n"
        "REGRAS OBRIGATÓRIAS:\n"
        "1) Se fornecedor.ativo=False (0), REJEITAR IMEDIATAMENTE, independentemente de outros fatores.\n"
        "2) Se existir pelo menos uma ordem APROVADA do mesmo fornecedor, com valor dentro de +/-20%, então APROVAR.\n"
        "3) Caso contrário, REJEITAR.\n\n"
        "Respondes apenas com 'APROVAR' ou 'REJEITAR'."
    ),
)


def decide_approval(valor_total, fornecedor_id, resultados):
    print("==DEBUG== [decide_approval] Resultados obtidos:\n", resultados, "\n", flush=True)

    if not resultados or len(resultados) == 0:
        print("==ERRO== [decide_approval] Nenhuma ordem encontrada para análise!", flush=True)
        return "REJEITAR"

    # Verifica se o fornecedor está ativo
    fornecedor_ativo = any(
        row[-1] in [1, True, "1", "true"]  
        for row in resultados
    )
    if not fornecedor_ativo:
        print("==ERRO== [decide_approval] Fornecedor está inativo. REJEITADO imediatamente.", flush=True)
        return "REJEITAR"

    # Converte os resultados para JSON formatado antes de enviar ao LLM
    resultados_str = json.dumps(resultados, indent=2, ensure_ascii=False)
    prompt = approval_prompt_template.format(
        valor_total=valor_total,
        fornecedor_id=fornecedor_id,
        resultados=resultados_str
    )

    print("==DEBUG== [decide_approval] Prompt de aprovação:\n", prompt, "\n", flush=True)

    response = llm.invoke(prompt)
    
    # Verifica se a resposta do LLM está vazia
    if not response or not response.content.strip():
        print("==ERRO== [decide_approval] O LLM não retornou uma resposta válida!", flush=True)
        return "REJEITAR"

    final_answer = response.content.strip().upper()

    print("==DEBUG== [decide_approval] Resposta final do LLM:\n", final_answer, "\n", flush=True)
    return final_answer



if __name__ == "__main__":
    # Esperamos que o Node chame: python3 sql_agent.py <valor_total> <fornecedor_id>
    if len(sys.argv) < 3:
        print("ERRO: argumentos insuficientes. Uso: python3 sql_agent.py <valor_total> <fornecedor_id>", file=sys.stderr)
        sys.exit(1)

    valor_total = sys.argv[1]
    fornecedor_id = sys.argv[2]

    try:
        # 1. Gerar query
        query = write_query(valor_total, fornecedor_id)

        # 2. Executar query
        results = execute_query(query)

        # 3. Decidir se aprova ou não com base no LLM
        decision = decide_approval(valor_total, fornecedor_id, results)

        # 4. Imprimir no stdout a decisão final (usada pelo Node.js)
        #    "APROVAR" ou "REJEITAR".
        print(decision)

    except Exception as e:
        print(f"Erro: {str(e)}", file=sys.stderr)
        sys.exit(1)
