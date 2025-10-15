from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.base import BaseHook
from kafka import KafkaProducer
import pandas as pd
import json
import psycopg2
import pymysql

# ===================== Config =====================
KAFKA_HOST = "kafka:9092"

def serializer(message):
    """Serialize messages as JSON-encoded UTF-8 bytes."""
    return json.dumps(message, default=str).encode("utf-8")

# ===================== Database Connections =====================

def extract_from_postgresql():
    """Extraer datos de PostgreSQL usando Airflow Connections"""
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_HOST],
        value_serializer=serializer
    )
    
    try:
        # Usando Airflow Connection (configurar en UI: Admin -> Connections)
        # conn_id = 'postgres_default'
        # connection = BaseHook.get_connection(conn_id)
        
        # Conexión directa (para demo)
        conn = psycopg2.connect(
            host="postgres",  # Servicio de docker-compose
            port=5432,
            database="druid",
            user="druid",
            password="FoolishPassword"
        )
        
        # Real query example - replace with your actual table queries
        # For GOES satellite data, you might query:
        # query = """
        # SELECT product_time, time, solar_array_current_channel_index_label,
        #        irradiance_xrsa1, irradiance_xrsa2, irradiance_xrsb1, irradiance_xrsb2,
        #        primary_xrsb, dispersion_angle, integration_time
        # FROM goes_satellite_data 
        # WHERE product_time >= NOW() - INTERVAL '1 hour'
        # """
        
        # Temporary synthetic query (REMOVE when you have real data)
        query = """
        SELECT 
            EXTRACT(EPOCH FROM NOW()) as timestamp,
            'user_' || generate_series(1,50) as user_id,
            random() * 1000 as revenue,
            case when random() > 0.5 then 'premium' else 'basic' end as plan_type,
            case when random() > 0.7 then 'web' else 'mobile' end as platform
        LIMIT 100
        """
        
        df = pd.read_sql(query, conn)
        
        for _, row in df.iterrows():
            record = row.to_dict()
            record["source"] = "postgresql"
            
            producer.send("database_users", record)
        
        print(f"Extraídos {len(df)} registros de PostgreSQL")
        
        conn.close()
        
    except Exception as e:
        print(f"Error extrayendo de PostgreSQL: {e}")
    finally:
        producer.flush()
        producer.close()

def extract_from_mysql():
    """Extraer datos de MySQL"""
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_HOST],
        value_serializer=serializer
    )
    
    try:
        # Configuración para MySQL externo (ejemplo)
        conn = pymysql.connect(
            host='your-mysql-host',
            port=3306,
            user='your-user',
            password='your-password',
            database='your-database',
            charset='utf8mb4'
        )
        
        # Consulta incremental - solo nuevos datos
        query = """
        SELECT 
            id,
            customer_id,
            order_amount,
            order_date,
            status,
            payment_method,
            UNIX_TIMESTAMP(order_date) as timestamp
        FROM orders 
        WHERE order_date >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
        ORDER BY order_date DESC
        """
        
        df = pd.read_sql(query, conn)
        
        for _, row in df.iterrows():
            record = row.to_dict()
            record["source"] = "mysql_orders"
            
            producer.send("order_data", record)
        
        print(f"Extraídos {len(df)} pedidos de MySQL")
        
        conn.close()
        
    except Exception as e:
        print(f"Error extrayendo de MySQL: {e}")
    finally:
        producer.flush()
        producer.close()

def extract_from_mongodb():
    """Extraer datos de MongoDB"""
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_HOST],
        value_serializer=serializer
    )
    
    try:
        from pymongo import MongoClient
        
        # Conectar a MongoDB
        client = MongoClient('mongodb://your-mongo-host:27017/')
        db = client['your-database']
        collection = db['user_events']
        
        # Consulta de eventos recientes
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        cursor = collection.find({
            "timestamp": {"$gte": one_hour_ago}
        })
        
        count = 0
        for document in cursor:
            # Convertir ObjectId a string
            document["_id"] = str(document["_id"])
            document["timestamp"] = int(document["timestamp"].timestamp())
            document["source"] = "mongodb_events"
            
            producer.send("user_events", document)
            count += 1
        
        print(f"Extraídos {count} eventos de MongoDB")
        
        client.close()
        
    except Exception as e:
        print(f"Error extrayendo de MongoDB: {e}")
    finally:
        producer.flush()
        producer.close()

def extract_from_s3_files():
    """Extraer datos de archivos en S3/MinIO"""
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_HOST],
        value_serializer=serializer
    )
    
    try:
        import boto3
        
        # Configurar cliente S3
        s3_client = boto3.client(
            's3',
            endpoint_url='http://your-minio-endpoint:9000',
            aws_access_key_id='your-access-key',
            aws_secret_access_key='your-secret-key'
        )
        
        bucket = 'data-lake'
        prefix = 'raw-data/events/'
        
        # Listar archivos nuevos
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        
        for obj in response.get('Contents', []):
            if obj['Key'].endswith('.json'):
                # Descargar y procesar archivo
                response = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                data = json.loads(response['Body'].read())
                
                for record in data:
                    record["source"] = "s3_files"
                    record["file_name"] = obj['Key']
                    
                    producer.send("s3_data", record)
                
                print(f"Procesado archivo S3: {obj['Key']}")
        
    except Exception as e:
        print(f"Error extrayendo de S3: {e}")
    finally:
        producer.flush()
        producer.close()

def extract_log_files():
    """Extraer y procesar logs de aplicaciones"""
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_HOST],
        value_serializer=serializer
    )
    
    try:
        import re
        
        # Patrón para logs de acceso web
        log_pattern = r'(\S+) - - \[(.*?)\] "(\S+) (\S+) (\S+)" (\d+) (\d+) "([^"]*)" "([^"]*)"'
        
        # Procesar archivo de log (simulado)
        log_entries = [
            '192.168.1.1 - - [01/Jul/2025:10:00:00 +0000] "GET /api/users HTTP/1.1" 200 1234 "https://example.com" "Mozilla/5.0"',
            '192.168.1.2 - - [01/Jul/2025:10:01:00 +0000] "POST /api/orders HTTP/1.1" 201 567 "https://example.com" "Chrome/91.0"',
            '192.168.1.3 - - [01/Jul/2025:10:02:00 +0000] "GET /dashboard HTTP/1.1" 200 2345 "https://example.com" "Firefox/89.0"'
        ]
        
        for log_line in log_entries:
            match = re.match(log_pattern, log_line)
            if match:
                record = {
                    "timestamp": int(datetime.now().timestamp()),
                    "ip_address": match.group(1),
                    "method": match.group(3),
                    "url": match.group(4),
                    "status_code": int(match.group(6)),
                    "response_size": int(match.group(7)),
                    "referer": match.group(8),
                    "user_agent": match.group(9),
                    "source": "web_logs"
                }
                
                producer.send("web_access_logs", record)
        
        print("Procesados logs de acceso web")
        
    except Exception as e:
        print(f"Error procesando logs: {e}")
    finally:
        producer.flush()
        producer.close()

# ===================== DAG Definition =====================

default_args = {
    "owner": "data_engineer",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5)
}

with DAG(
    dag_id="database_etl_pipeline",
    description="Pipeline ETL para extraer datos de bases de datos y sistemas existentes",
    default_args=default_args,
    schedule='*/30 * * * *',  # Cada 30 minutos
    catchup=False,
    tags=["production", "databases", "etl"]
) as dag:

    # Extracción de bases de datos
    postgres_task = PythonOperator(
        task_id="extract_from_postgresql",
        python_callable=extract_from_postgresql
    )
    
    # Nota: Descomenta estas tareas si tienes las conexiones configuradas
    # mysql_task = PythonOperator(
    #     task_id="extract_from_mysql",
    #     python_callable=extract_from_mysql
    # )
    
    # mongodb_task = PythonOperator(
    #     task_id="extract_from_mongodb", 
    #     python_callable=extract_from_mongodb
    # )
    
    # s3_task = PythonOperator(
    #     task_id="extract_from_s3",
    #     python_callable=extract_from_s3_files
    # )
    
    logs_task = PythonOperator(
        task_id="extract_log_files",
        python_callable=extract_log_files
    )
    
    # Ejecutar tareas disponibles
    [postgres_task, logs_task]
