import os
os.environ['CASS_DRIVER_GEVENT_PATCH'] = 'true'

import time
import random
from datetime import datetime
from cassandra.cluster import Cluster
from cassandra.protocol import SyntaxException, InvalidRequest

class DataGenerator:
    def __init__(self):
        self.cluster = None
        try:
            self.cluster = Cluster(['127.0.0.1'])
            self.session = self.cluster.connect()
            self.session.set_keyspace('btc')
            self.sequential_id = 1
            self.load_last_sequential_id()
            print("Conexão com Cassandra estabelecida com sucesso.")
        except Exception as e:
            print(f"Não foi possível conectar ao Cassandra: {e}")
            exit()

    def load_last_sequential_id(self):
        try:
            now = datetime.now()
            today_str = now.strftime('%Y_%m_%d')
            table_name = f"random_data_{today_str}"
            day_partition = now.strftime('%Y-%m-%d')

            query = f"""CREATE TABLE IF NOT EXISTS {table_name} (
                day_partition TEXT,
                sequential_id INT,
                dia_tempo TIMESTAMP,
                random_number INT,
                PRIMARY KEY (day_partition, sequential_id)
            ) WITH CLUSTERING ORDER BY (sequential_id ASC);"""
            self.session.execute(query)

            query = f"SELECT MAX(sequential_id) as max_id FROM {table_name} WHERE day_partition = %s"
            result = self.session.execute(query, (day_partition,))
            row = result.one()
            if row and row.max_id is not None:
                self.sequential_id = row.max_id + 1
            else:
                self.sequential_id = 1
            print(f"ID sequencial inicializado em: {self.sequential_id} para a tabela {table_name}")
        except Exception as e:
            print(f"Não foi possível carregar o último ID sequencial, iniciando em 1. Erro: {e}")
            self.sequential_id = 1

    def generate_and_save_data(self):
        try:
            random_num = random.randint(1, 1000)
            current_time = datetime.now()
            day_partition = current_time.strftime('%Y-%m-%d')
            today_str = current_time.strftime('%Y_%m_%d')
            table_name = f"random_data_{today_str}"

            query = f"INSERT INTO {table_name} (day_partition, sequential_id, dia_tempo, random_number) VALUES (%s, %s, %s, %s)"
            self.session.execute(query, (day_partition, self.sequential_id, current_time, random_num))

            print(f"Dado inserido: ID {self.sequential_id}, Número {random_num}")
            self.sequential_id += 1

        except (SyntaxException, InvalidRequest) as e:
            print(f"Erro de Query: {e}")
        except Exception as e:
            print(f"Erro inesperado: {e}")

    def run(self):
        print("Iniciando gerador de dados... Pressione Ctrl+C para parar.")
        try:
            while True:
                self.generate_and_save_data()
                time.sleep(2)  # Espera 2 segundos para inserir o próximo dado
        except KeyboardInterrupt:
            print("\nGerador de dados parado.")
        finally:
            if self.cluster:
                self.cluster.shutdown()

if __name__ == "__main__":
    generator = DataGenerator()
    generator.run()