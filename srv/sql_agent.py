import os
import sys
import getpass
import json
import re
from datetime import datetime
from langchain_community.utilities import SQLDatabase
from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate

# Desativar LangSmith e evitar conexões desnecessárias
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Obter API Key para a Groq (caso necessário)
if not os.environ.get("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = getpass.getpass("Enter API key for Groq: ")

# Inicializar LLM (ajuste conforme teu modelo ou provider)
llm = init_chat_model("llama3-8b-8192", model_provider="groq")

# Conectar ao SQLite
db = SQLDatabase.from_uri("sqlite:///db.sqlite")

def get_table_info():
    tables = db.get_usable_table_names()
    if not tables:
        raise ValueError("Nenhuma tabela encontrada no banco!")
    table_info = { table: db.get_table_info([table]) for table in tables }
    return table_info

def clean_query(query):
    """Remove formatação extra (blocos ```sql ...``` ) da query gerada pelo LLM."""
    query = re.sub(r"```sql\s*([\s\S]*?)\s*```", r"\1", query)
    return query.strip()

# Simulação de feriados
FERIADOS = {
    # yyyy-mm-dd ou só mm-dd se preferires
    "2025-03-07",  # Exemplo de feriado
}

def is_special_date(dt_str):
    """
    Verifica se a data está em fins de semana ou é um feriado conhecido.
    dt_str = '2025-03-07T09:00:00Z' ou similar.
    """
    if not dt_str:
        return False

    # Tentar converter para datetime
    try:
        # Remove 'Z' se houver e converte
        dt = datetime.fromisoformat(dt_str.replace("Z",""))
    except:
        return False

    # 1) Verifica se é fim de semana (Sat=6, Sun=7)
    if dt.isoweekday() >= 6:
        return True

    # 2) Verifica se é feriado
    dt_date_str = dt.strftime("%Y-%m-%d")
    if dt_date_str in FERIADOS:
        return True

    return False

# -----------------------------------------------------------------------------
# 1) CONSULTA PRINCIPAL (ordens em ±20% do valor_total, mesmo fornecedor)
# -----------------------------------------------------------------------------
similar_orders_prompt = PromptTemplate(
    input_variables=["table_info", "valor_total", "fornecedor_id"],
    template=(
        "Temos as tabelas a seguir, com suas colunas:\n"
        "{table_info}\n\n"
        "Gere uma query SQL que:\n"
        "1) Consulte as ordens 'my_orders_Order' (chame-as de 'o') do mesmo fornecedor {fornecedor_id}.\n"
        "2) Filtre apenas ordens com valor_total dentro de +/- 20% de {valor_total}.\n"
        "3) Faça JOIN em my_orders_Fornecedor (chame-o de 'f') para verificar se f.ativo.\n"
        "4) Se possível, inclua status, previsao_entrega, data_entrega.\n"
        "5) NÃO use 'f.nome', e sim 'f.name'. Inclua também 'f.ativo'.\n\n"
        "Retorne APENAS a query SQL pura, sem blocos ```sql```."
    ),
)

def write_query_similar_orders(valor_total, fornecedor_id):
    table_info = get_table_info()
    prompt = similar_orders_prompt.format(
        table_info=table_info,
        valor_total=valor_total,
        fornecedor_id=fornecedor_id,
    )

    print("==DEBUG== [write_query_similar_orders] Prompt:\n", prompt, "\n", flush=True)
    response = llm.invoke(prompt)
    raw_query = response.content if hasattr(response, "content") else response

    print("==DEBUG== [write_query_similar_orders] Query bruta:\n", raw_query, "\n", flush=True)
    query = clean_query(raw_query)
    print("==DEBUG== [write_query_similar_orders] Query final:\n", query, "\n", flush=True)
    return query

# -----------------------------------------------------------------------------
# 2) CONSULTA ESTATÍSTICA DE ENTREGA (para ver se o fornecedor cumpre prazos)
# -----------------------------------------------------------------------------
delivery_stats_prompt = PromptTemplate(
    input_variables=["table_info", "fornecedor_id"],
    template=(
        "Temos as tabelas:\n"
        "{table_info}\n\n"
        "Gere uma query SQL que:\n"
        "1) Consulte a tabela my_orders_Order (chame-a de 'o').\n"
        "2) Traga colunas: o.numero, o.previsao_entrega, o.data_entrega, o.status.\n"
        "3) Filtre apenas o.fornecedor_ID = '{fornecedor_id}'.\n"
        "4) Retorne APENAS a query SQL pura."
    ),
)

def write_query_delivery_stats(fornecedor_id):
    table_info = get_table_info()
    prompt = delivery_stats_prompt.format(
        table_info=table_info,
        fornecedor_id=fornecedor_id,
    )

    print("==DEBUG== [write_query_delivery_stats] Prompt:\n", prompt, "\n", flush=True)
    response = llm.invoke(prompt)
    raw_query = response.content if hasattr(response, "content") else response

    print("==DEBUG== [write_query_delivery_stats] Query bruta:\n", raw_query, "\n", flush=True)
    query = clean_query(raw_query)
    print("==DEBUG== [write_query_delivery_stats] Query final:\n", query, "\n", flush=True)
    return query

# -----------------------------------------------------------------------------
# 3) CONSULTA PREÇOS DE MATERIAIS (para comparar valores entre fornecedores)
# -----------------------------------------------------------------------------
material_stats_prompt = PromptTemplate(
    input_variables=["table_info"],
    template=(
        "Com base nas tabelas:\n"
        "{table_info}\n\n"
        "Gere uma query SQL que:\n"
        "1) Faça join em my_orders_OrderMaterial (chame de 'om') e my_orders_Order (chame de 'o') e Fornecedor (chame de 'f').\n"
        "2) Calcule o preço efetivo (om.subtotal / om.quantidade) como 'price_each'.\n"
        "3) Traga: om.material_ID, f.ID AS fornecedor_ID, price_each.\n"
        "4) Retorne TODAS as linhas para poder calcular a média em Python.\n"
        "5) Retorne APENAS a query SQL pura."
    ),
)

def write_query_material_stats():
    table_info = get_table_info()
    prompt = material_stats_prompt.format(table_info=table_info)

    print("==DEBUG== [write_query_material_stats] Prompt:\n", prompt, "\n", flush=True)
    response = llm.invoke(prompt)
    raw_query = response.content if hasattr(response, "content") else response

    print("==DEBUG== [write_query_material_stats] Query bruta:\n", raw_query, "\n", flush=True)
    query = clean_query(raw_query)
    print("==DEBUG== [write_query_material_stats] Query final:\n", query, "\n", flush=True)
    return query

# -----------------------------------------------------------------------------
# Execução genérica de queries
# -----------------------------------------------------------------------------
def execute_query(query):
    print(f"==DEBUG== [execute_query] Executando:\n{query}\n", flush=True)
    try:
        if "f.nome" in query:
            raise ValueError("ERRO: Query inválida. A coluna correta é 'f.name', não 'f.nome'.")
        results = db.run(query)
        print("==DEBUG== [execute_query] Resultado:\n", results, "\n", flush=True)
        return results
    except Exception as e:
        print(f"==ERRO== [execute_query] Problema ao executar a query: {str(e)}", flush=True)
        return []

# -----------------------------------------------------------------------------
# 4) LÓGICA OU PROMPT DE APROVAÇÃO (com explicabilidade e fator externo)
# -----------------------------------------------------------------------------

approval_prompt_template = PromptTemplate(
    input_variables=[
        "valor_total",
        "fornecedor_id",
        "supplier_delivery_info",
        "similar_orders",
        "material_stats",
        "new_order_materials",
        "external_factors"
    ],
    template=(
        "NOVA ORDEM:\n"
        "- valor_total={valor_total}\n"
        "- fornecedor_id={fornecedor_id}\n"
        "- Materiais da nova ordem: {new_order_materials}\n\n"
        "HISTÓRICO DE ENTREGA DESTE FORNECEDOR:\n"
        "{supplier_delivery_info}\n\n"
        "ORDENS SIMILARES (±20% do valor_total) COM MESMO FORNECEDOR:\n"
        "{similar_orders}\n\n"
        "PREÇOS DE MATERIAIS (price_each) DE TODOS OS FORNECEDORES:\n"
        "{material_stats}\n\n"
        "FATORES EXTERNOS:\n"
        "{external_factors}\n\n"
        "REGRAS OBRIGATÓRIAS:\n"
        "1) Se o fornecedor está inativo => REJEITAR.\n"
        "2) Se as ultimas ordens do fornecedor foram APROVADAS no histórico (entre semelhantes) => tende a APROVAR.\n"
        "3) Se o fornecedor atrasa SEMPRE (data_entrega muito após previsao_entrega), pode REJEITAR.\n"
        "4) Se os materiais desta nova ordem estão muito acima da média de outros fornecedores, sugira REJEITAR.\n"
        "5) Se o dia de entrega for feriado ou fim de semana, deve REJEITAR.\n\n"
        "Responda APENAS com 'APROVAR' ou 'REJEITAR'."
    ),
)

explanation_prompt_template = PromptTemplate(
    input_variables=[
        "decision",
        "valor_total",
        "fornecedor_id",
        "external_factors"
    ],
    template=(
        "A decisão final para esta ordem foi: {decision}.\n\n"
        "Explique resumidamente (1-2 frases) por que a ordem com valor_total={valor_total}, fornecedor_id={fornecedor_id},\n"
        "e fatores externos {external_factors}, foi {decision}."
    ),
)

def decide_approval(
    valor_total,
    fornecedor_id,
    supplier_delivery_info,
    similar_orders,
    material_stats,
    new_order_materials,
    external_factors
):
    """
    Aplica a lógica via LLM, considerando vários fatores além de valor total e fornecedor ativo:
    - Histórico de entrega
    - Preços médios de materiais
    - Checagem de feriado / fim de semana (passada como external_factors)
    """

    supplier_delivery_str = json.dumps(supplier_delivery_info, indent=2, ensure_ascii=False)
    similar_orders_str = json.dumps(similar_orders, indent=2, ensure_ascii=False)
    material_stats_str = json.dumps(material_stats, indent=2, ensure_ascii=False)
    new_order_materials_str = json.dumps(new_order_materials, indent=2, ensure_ascii=False)
    external_factors_str = json.dumps(external_factors, indent=2, ensure_ascii=False)

    prompt = approval_prompt_template.format(
        valor_total=valor_total,
        fornecedor_id=fornecedor_id,
        supplier_delivery_info=supplier_delivery_str,
        similar_orders=similar_orders_str,
        material_stats=material_stats_str,
        new_order_materials=new_order_materials_str,
        external_factors=external_factors_str
    )

    print("==DEBUG== [decide_approval] Prompt final:\n", prompt, "\n", flush=True)

    response = llm.invoke(prompt)
    if not response or not response.content.strip():
        print("==ERRO== [decide_approval] LLM não retornou resposta!", flush=True)
        return "REJEITAR"

    final_answer = response.content.strip().upper()
    print("==DEBUG== [decide_approval] Resposta LLM:", final_answer, flush=True)
    return final_answer

def generate_explanation(decision, valor_total, fornecedor_id, external_factors):
    """
    Gera uma explicação curta (1-2 frases) sobre a decisão tomada.
    """
    prompt = explanation_prompt_template.format(
        decision=decision,
        valor_total=valor_total,
        fornecedor_id=fornecedor_id,
        external_factors=external_factors
    )
    print("==DEBUG== [generate_explanation] Prompt:\n", prompt, "\n", flush=True)

    response = llm.invoke(prompt)
    if not response or not response.content.strip():
        return "Não foi possível gerar justificativa."

    return response.content.strip()

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    """
    Uso esperado:
       python3 sql_agent.py <valor_total> <fornecedor_id> [previsao_entrega] [data_entrega] [json_materiais]
    """
    if len(sys.argv) < 3:
        print("ERRO: argumentos insuficientes. Uso: python3 sql_agent.py <valor_total> <fornecedor_id>", file=sys.stderr)
        sys.exit(1)

    valor_total = sys.argv[1]
    fornecedor_id = sys.argv[2]

    # Podem ser passadas no CLI, senão None
    previsao_entrega = sys.argv[3] if len(sys.argv) >= 4 else None
    data_entrega = sys.argv[4] if len(sys.argv) >= 5 else None

    # Materiais da nova ordem em formato JSON
    new_order_materials = []
    if len(sys.argv) >= 6:
        try:
            new_order_materials = json.loads(sys.argv[5])
        except:
            new_order_materials = []

    # 1) Query de ordens semelhantes
    query_similar = write_query_similar_orders(valor_total, fornecedor_id)
    similar_orders = execute_query(query_similar)

    # 2) Query de estatísticas de entrega (histórico)
    query_delivery = write_query_delivery_stats(fornecedor_id)
    supplier_delivery_info = execute_query(query_delivery)

    # 3) Query de estatísticas de materiais
    query_material_stats = write_query_material_stats()
    all_material_stats = execute_query(query_material_stats)

    # 4) Integração com dados externos (feriado/fim de semana)
    external_factors = {}
    if is_special_date(previsao_entrega):
        external_factors["previsao_entrega"] = "feriado ou fim-de-semana"
    if is_special_date(data_entrega):
        external_factors["data_entrega"] = "feriado ou fim-de-semana"

    # (Opcional) Podes forçar rejeição se preferires, mas aqui deixamos para o LLM.
    if external_factors:
        print(f"==INFO== [main] Há fatores externos que afetam a entrega: {external_factors}", flush=True)

    # 5) Decidir aprovação, considerando tudo
    decision = decide_approval(
        valor_total=valor_total,
        fornecedor_id=fornecedor_id,
        supplier_delivery_info=supplier_delivery_info,
        similar_orders=similar_orders,
        material_stats=all_material_stats,
        new_order_materials=new_order_materials,
        external_factors=external_factors
    )

    # 6) Gerar explicação curta
    explanation = generate_explanation(decision, valor_total, fornecedor_id, external_factors)

    # 7) Imprimir JSON final no stdout, para ser capturado pelo Node.js
    output = {
        "decision": decision,
        "explanation": explanation
    }
    print(json.dumps(output, ensure_ascii=False))
