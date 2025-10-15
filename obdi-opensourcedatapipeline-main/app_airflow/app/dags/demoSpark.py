from datetime import datetime, timedelta
from airflow.models import DAG
from airflow.operators.python import PythonOperator
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from kafka import KafkaProducer
import random
import json

def serializer(message):
    """Serialize messages as JSON-encoded UTF-8 bytes."""
    return json.dumps(message).encode("utf-8")

def run_spark_job():
    spark = SparkSession.builder \
        .master("spark://spark:7077") \
        .appName("Airflow-Spark Analytics Job") \
        .config("spark.ui.showConsoleProgress", "false") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Configurar Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=["kafka:9092"],
        value_serializer=serializer
    )
    
    # Generar datos sintéticos de analytics
    current_time = int(datetime.now().timestamp())
    analytics_data = []
    
    for i in range(100):
        record = {
            "session_id": f"session_{random.randint(1000, 9999)}",
            "user_id": random.randint(1, 500),
            "page_views": random.randint(1, 20),
            "time_spent_minutes": random.randint(1, 120),
            "device_type": random.choice(["mobile", "desktop", "tablet"]),
            "country": random.choice(["US", "UK", "DE", "FR", "ES", "IT", "JP"]),
            "timestamp": current_time + random.randint(-3600, 0),
            "revenue": round(random.uniform(0, 500), 2) if random.random() > 0.7 else 0
        }
        analytics_data.append(record)
        
        # Enviar a Kafka para que Druid lo consuma
        producer.send("spark_analytics", record)
    
    # Crear DataFrame para análisis en Spark
    schema = StructType([
        StructField("session_id", StringType(), True),
        StructField("user_id", IntegerType(), True),
        StructField("page_views", IntegerType(), True),
        StructField("time_spent_minutes", IntegerType(), True),
        StructField("device_type", StringType(), True),
        StructField("country", StringType(), True),
        StructField("timestamp", LongType(), True),
        StructField("revenue", DoubleType(), True)
    ])
    
    df = spark.createDataFrame(analytics_data, schema)
    
    # Realizar análisis
    print("=== Análisis de Datos de Usuario ===")
    
    # Métricas por país
    country_stats = df.groupBy("country") \
        .agg(
            count("*").alias("sessions"),
            avg("page_views").alias("avg_page_views"),
            sum("revenue").alias("total_revenue")
        ) \
        .orderBy(desc("sessions"))
    
    print("Top países por sesiones:")
    country_stats.show()
    
    # Métricas por dispositivo
    device_stats = df.groupBy("device_type") \
        .agg(
            count("*").alias("sessions"),
            avg("time_spent_minutes").alias("avg_time_spent"),
            sum("revenue").alias("total_revenue")
        )
    
    print("Estadísticas por dispositivo:")
    device_stats.show()
    
    # Usuarios de alto valor (más de 100 en revenue)
    high_value_users = df.filter(col("revenue") > 100) \
        .select("user_id", "revenue", "device_type", "country") \
        .orderBy(desc("revenue"))
    
    print("Usuarios de alto valor:")
    high_value_users.show()
    
    print(f"Total de sesiones procesadas: {df.count()}")
    print(f"Revenue total: ${df.agg(sum('revenue')).collect()[0][0]:.2f}")
    
    # Cerrar conexiones
    producer.flush()
    producer.close()
    spark.stop()

#  ===================== DAG Definition  =====================
default_args = {
    "retries": 2,
    "retry_delay": timedelta(seconds=30)
}

with DAG(
    dag_id="spark_batch_job",
    description="DISABLED - This DAG generates synthetic analytics data for Spark processing.",
    schedule=None,                      # DISABLED - was '*/1 * * * *'
    start_date=datetime(2022, 2, 26), 
    catchup=False,
    is_paused_upon_creation=True,       # Start paused
    tags=["demo", "disabled"]
) as dag:
    
    spark_task = PythonOperator(
        task_id="run_spark",
        python_callable=run_spark_job
    )

    spark_task
