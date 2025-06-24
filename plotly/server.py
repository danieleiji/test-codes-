import os
os.environ['CASS_DRIVER_GEVENT_PATCH'] = 'true'
import gevent # Adicionado para garantir que o patch seja aplicado

import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from cassandra.cluster import Cluster
import os # Adicionado para o caminho relativo

app = FastAPI()

# Obter o diretório do script atual para construir o caminho relativo
script_dir = os.path.dirname(__file__)
html_file_path = os.path.join(script_dir, "templates", "index.html")


# --- Conexão com o Cassandra ---
def get_cassandra_session():
    try:
        cluster = Cluster(['127.0.0.1'])
        session = cluster.connect('btc')
        print("Conexão com Cassandra estabelecida para o servidor.")
        return cluster, session
    except Exception as e:
        print(f"Erro ao conectar com Cassandra no servidor: {e}")
        return None, None

cluster, session = get_cassandra_session()

# --- WebSocket para enviar dados em tempo real ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    last_sent_id = 0

    try:
        while True:
            if not session:
                await websocket.send_text("Erro: Sem conexão com o banco de dados.")
                await asyncio.sleep(5)
                continue

            now = datetime.now()
            today_str = now.strftime('%Y_%m_%d')
            table_name = f"random_data_{today_str}"
            day_partition = now.strftime('%Y-%m-%d')

            try:
                # Busca o ID máximo atual na tabela
                query_max_id = f"SELECT MAX(sequential_id) as max_id FROM {table_name} WHERE day_partition = %s"
                result_max_id = session.execute(query_max_id, (day_partition,))
                max_id_in_db = result_max_id.one().max_id

                if max_id_in_db is not None and max_id_in_db > last_sent_id:
                    # Busca todos os dados novos desde a última verificação
                    query_new_data = f"SELECT sequential_id, random_number FROM {table_name} WHERE day_partition = %s AND sequential_id > %s"
                    rows = session.execute(query_new_data, (day_partition, last_sent_id))
                    
                    new_data = []
                    for row in rows:
                        new_data.append({"id": row.sequential_id, "value": row.random_number})
                        last_sent_id = row.sequential_id # Atualiza o último ID enviado

                    if new_data:
                        await websocket.send_text(json.dumps(new_data))

            except Exception as e:
                # Ignora erros se a tabela ainda não existir, por exemplo
                pass

            await asyncio.sleep(1) # Verifica por novos dados a cada segundo

    except WebSocketDisconnect:
        print("Cliente desconectado.")
    except Exception as e:
        print(f"Ocorreu um erro no WebSocket: {e}")
    finally:
        await websocket.close()

# --- Rota para servir o arquivo HTML ---
@app.get("/")
async def get():
    with open(html_file_path) as f:
        return HTMLResponse(f.read())

# --- Para fechar a conexão ao parar o servidor ---
@app.on_event("shutdown")
def shutdown_event():
    if cluster:
        cluster.shutdown()
        print("Conexão com Cassandra fechada.")