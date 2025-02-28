import sqlite3
import sys

# Caminho da base de dados
db_path = "./db.sqlite"  

def connect_db():
    """Conecta à base de dados CAP SQLite."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        print(f"Erro ao conectar à base de dados: {e}")
        sys.exit(1)

def approve_order(order_id):
    """Aprova a ordem de compra alterando o status para 'APROVADO'."""
    conn, cursor = connect_db()

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]
        print(f"Tabelas disponíveis: {tables}")

        table_name = "my_orders_Order" 

        cursor.execute(f"UPDATE {table_name} SET status = ? WHERE ID = ?", ("APROVADO", order_id))
        conn.commit()

        if cursor.rowcount == 0:
            print(f"Nenhuma ordem encontrada com ID {order_id}.")
        else:
            print(f"Ordem {order_id} aprovada com sucesso.")
    except Exception as e:
        print(f"Erro ao aprovar ordem: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "approve":
        approve_order(sys.argv[2])
    else:
        print("Comando inválido. Use: python3 script.py approve <orderID>")
