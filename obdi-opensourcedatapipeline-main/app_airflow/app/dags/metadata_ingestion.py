from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import requests
import json
import time
import os

# ===================== Config =====================
OPENMETADATA_HOST = "http://openmetadata:8585"

# ===================== Helper Functions =====================
def load_ingestion_config(file_path):
    """Load ingestion config from JSON file"""
    with open(file_path, 'r') as file:
        return json.load(file)

def trigger_ingestion(config_file):
    """Trigger OpenMetadata ingestion pipeline"""
    config = load_ingestion_config(config_file)
    
    # Wait for OpenMetadata to be ready
    max_retries = 10
    retry_count = 0
    while retry_count < max_retries:
        try:
            health_check = requests.get(f"{OPENMETADATA_HOST}/healthcheck", timeout=5)
            if health_check.status_code == 200:
                break
            retry_count += 1
            time.sleep(30)
        except Exception as e:
            print(f"OpenMetadata not ready yet, retrying in 30 seconds... Error: {e}")
            retry_count += 1
            time.sleep(30)
    
    if retry_count == max_retries:
        raise Exception("OpenMetadata service is not available after maximum retries")
    
    # Create or get service
    service_name = config["source"]["serviceName"]
    service_type = config["source"]["type"]
    
    # Create the pipeline
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{OPENMETADATA_HOST}/api/v1/services/{service_type}/testConnection",
            headers=headers,
            data=json.dumps(config["source"]["serviceConnection"])
        )
        print(f"Test connection response: {response.status_code}")
        print(response.text)
        
        # Create and trigger ingestion pipeline
        response = requests.post(
            f"{OPENMETADATA_HOST}/api/v1/ingestion/workflows",
            headers=headers,
            data=json.dumps(config)
        )
        
        if response.status_code in (200, 201):
            workflow_id = response.json().get("id")
            print(f"Successfully created ingestion workflow: {workflow_id}")
            
            # Trigger the pipeline to run
            deploy_response = requests.post(
                f"{OPENMETADATA_HOST}/api/v1/ingestion/workflows/deploy/{workflow_id}",
                headers=headers
            )
            
            if deploy_response.status_code == 200:
                print(f"Successfully triggered ingestion for {service_name}")
            else:
                print(f"Failed to trigger ingestion: {deploy_response.status_code}")
                print(deploy_response.text)
        else:
            print(f"Failed to create ingestion workflow: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error in OpenMetadata ingestion: {e}")

def ingest_druid_metadata():
    """Ingest Druid metadata to OpenMetadata"""
    trigger_ingestion("/airflow/openmetadata/druid-metadata-ingest.json")

def ingest_kafka_metadata():
    """Ingest Kafka metadata to OpenMetadata"""
    trigger_ingestion("/airflow/openmetadata/kafka-metadata-ingest.json")

def ingest_airflow_metadata():
    """Ingest Airflow metadata to OpenMetadata"""
    trigger_ingestion("/airflow/openmetadata/airflow-metadata-ingest.json")

def ingest_superset_metadata():
    """Ingest Superset metadata to OpenMetadata"""
    trigger_ingestion("/airflow/openmetadata/superset-metadata-ingest.json")

# ===================== DAG Definition =====================
default_args = {
    "owner": "data_engineer",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5)
}

with DAG(
    dag_id="openmetadata_ingestion",
    description="Pipeline for ingesting metadata from all sources",
    default_args=default_args,
    schedule='0 */4 * * *',  # Every 4 hours
    catchup=False,
    tags=["metadata", "ingestion"]
) as dag:

    # Wait for services to be ready
    wait_for_services = BashOperator(
        task_id="wait_for_services",
        bash_command="sleep 120"  # Wait 2 minutes for services to be ready
    )
    
    # Metadata ingestion tasks
    druid_metadata_task = PythonOperator(
        task_id="ingest_druid_metadata",
        python_callable=ingest_druid_metadata
    )
    
    kafka_metadata_task = PythonOperator(
        task_id="ingest_kafka_metadata",
        python_callable=ingest_kafka_metadata
    )
    
    airflow_metadata_task = PythonOperator(
        task_id="ingest_airflow_metadata",
        python_callable=ingest_airflow_metadata
    )
    
    superset_metadata_task = PythonOperator(
        task_id="ingest_superset_metadata",
        python_callable=ingest_superset_metadata
    )
    
    # Set up dependencies
    wait_for_services >> druid_metadata_task >> kafka_metadata_task >> airflow_metadata_task >> superset_metadata_task
