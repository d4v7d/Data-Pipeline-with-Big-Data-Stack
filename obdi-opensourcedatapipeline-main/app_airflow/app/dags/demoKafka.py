from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from kafka.errors import NoBrokersAvailable
from kafka import KafkaProducer
import random
import time
import json

# ===================== Config & Constants =====================
KAFKA_HOST_IP = "kafka"
KAFKA_PORT = 9092
TOPIC = "demo"
USER_IDS = list(range(1, 101))
RECIPIENT_IDS = list(range(1, 101))
COINS = ["BTC", "ETH", "BTT", "DOT"]

# ===================== Demo Functions =====================
def serializer(message):
    """Serialize messages as JSON-encoded UTF-8 bytes."""
    return json.dumps(message).encode("utf-8")


def generate_message():
    """Generate a sample message with random coin values."""
    random_user_id = random.choice(USER_IDS)
    recipient_ids_copy = RECIPIENT_IDS.copy()
    recipient_ids_copy.remove(random_user_id)

    timestamp = int(datetime.utcnow().timestamp())
    message = []

    for coin in COINS:
        if coin == "BTC":
            value = random.randint(10, 400)
        elif coin == "ETH":
            value = random.randint(10, 250)
        elif coin == "DOT":
            value = random.randint(40, 170)
        else:
            value = random.randint(10, 40)

        message.append({
            "data_id": value,
            "name": coin,
            "timestamp": timestamp
        })

    return message

# ===================== Kafka Function =====================

def produce_to_kafka():
    """Produce messages to Kafka topic."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=[f"{KAFKA_HOST_IP}:{KAFKA_PORT}"],
            value_serializer=serializer
        )
    except NoBrokersAvailable:
        print("Kafka not ready, retrying in 5 seconds...")
        time.sleep(5)
        producer = KafkaProducer(
            bootstrap_servers=[f"{KAFKA_HOST_IP}:{KAFKA_PORT}"],
            value_serializer=serializer
        )

    for msg in generate_message():
        print(f"Producing message @ {datetime.now()} | {msg}")
        producer.send(TOPIC, msg)

#  ===================== DAG Definition  =====================
default_args = {
    "retries": 2,
    "retry_delay": timedelta(seconds=30)
}

with DAG(
    dag_id="demo_producer_dag",
    description="DISABLED - This DAG sends synthetic crypto messages to Kafka.",
    schedule=None,                      # DISABLED - was '*/1 * * * *'
    start_date=datetime(2022, 2, 26),
    catchup=False,
    is_paused_upon_creation=True,       # Start paused
    tags=["demo", "disabled"]
) as dag:

    producer_task = PythonOperator(
        task_id="produce_kafka_messages",
        python_callable=produce_to_kafka
    )

    producer_task
    