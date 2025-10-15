from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from kafka import KafkaProducer
import requests
import pandas as pd
import json
import os

# ===================== Config =====================
KAFKA_HOST = "kafka:9092"

def serializer(message):
    """Serialize messages as JSON-encoded UTF-8 bytes."""
    return json.dumps(message).encode("utf-8")

# ===================== Extraction Functions =====================

def extract_crypto_prices():
    """Extraer precios reales de criptomonedas desde CoinGecko API"""
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_HOST],
        value_serializer=serializer
    )
    
    try:
        # API gratuita de CoinGecko
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'bitcoin,ethereum,cardano,polkadot',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_market_cap': 'true'
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        timestamp = int(datetime.now().timestamp())
        
        for coin, info in data.items():
            record = {
                "timestamp": timestamp,
                "coin_id": coin,
                "price_usd": info["usd"],
                "market_cap": info.get("usd_market_cap", 0),
                "change_24h": info.get("usd_24h_change", 0),
                "source": "coingecko_api"
            }
            
            print(f"Enviando precio real: {coin} = ${info['usd']}")
            producer.send("real_crypto_prices", record)
            
    except Exception as e:
        print(f"Error extrayendo precios crypto: {e}")
    finally:
        producer.flush()
        producer.close()

def extract_weather_data():
    """Extraer datos meteorológicos reales (requiere API key gratuita)"""
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_HOST],
        value_serializer=serializer
    )
    
    try:
        # obtener API key gratuita en openweathermap.org
        api_key = os.getenv('OPENWEATHER_API_KEY', 'mi_api_key_aqui')
        cities = ['San José', 'Heredia', 'Puntarenas', 'Alajuela', 'Limón']
        
        for city in cities:
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': city,
                'appid': api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                record = {
                    "timestamp": int(datetime.now().timestamp()),
                    "city": city,
                    "temperature": data["main"]["temp"],
                    "humidity": data["main"]["humidity"],
                    "pressure": data["main"]["pressure"],
                    "weather": data["weather"][0]["description"],
                    "wind_speed": data["wind"]["speed"]
                }
                
                print(f"Enviando datos meteorológicos: {city} = {data['main']['temp']}°C")
                producer.send("weather_data", record)
                
    except Exception as e:
        print(f"Error extrayendo datos meteorológicos: {e}")
    finally:
        producer.flush()
        producer.close()

def extract_stock_prices():
    """Extraer precios de acciones reales usando Alpha Vantage API"""
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_HOST],
        value_serializer=serializer
    )
    
    try:
        # API gratuita de Alpha Vantage
        api_key = os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        
        for symbol in symbols:
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if "Global Quote" in data:
                quote = data["Global Quote"]
                
                record = {
                    "timestamp": int(datetime.now().timestamp()),
                    "symbol": symbol,
                    "price": float(quote["05. price"]),
                    "change": float(quote["09. change"]),
                    "change_percent": quote["10. change percent"].strip('%'),
                    "volume": int(quote["06. volume"]),
                    "source": "alpha_vantage"
                }
                
                print(f"Enviando precio de acción: {symbol} = ${quote['05. price']}")
                producer.send("stock_prices", record)
                
    except Exception as e:
        print(f"Error extrayendo precios de acciones: {e}")
    finally:
        producer.flush()
        producer.close()

def process_csv_files():
    """Procesar archivos CSV de datos reales"""
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_HOST],
        value_serializer=serializer
    )
    
    try:
        # Directorio para archivos CSV
        csv_dir = "/tmp/data_files"
        processed_dir = "/tmp/processed_files"
        
        # Crear directorios si no existen
        os.makedirs(csv_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
        
        # Procesar archivos CSV
        for filename in os.listdir(csv_dir):
            if filename.endswith('.csv'):
                file_path = os.path.join(csv_dir, filename)
                
                try:
                    df = pd.read_csv(file_path)
                    
                    for _, row in df.iterrows():
                        record = row.to_dict()
                        record["timestamp"] = int(datetime.now().timestamp())
                        record["source_file"] = filename
                        
                        producer.send("csv_data", record)
                    
                    # Mover archivo procesado
                    processed_path = os.path.join(processed_dir, filename)
                    os.rename(file_path, processed_path)
                    
                    print(f"Procesado archivo: {filename} con {len(df)} registros")
                    
                except Exception as e:
                    print(f"Error procesando {filename}: {e}")
                    
    except Exception as e:
        print(f"Error en procesamiento de CSV: {e}")
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
    "retries": 2,
    "retry_delay": timedelta(minutes=5)
}

with DAG(
    dag_id="real_data_etl_pipeline",
    description="DISABLED - Pipeline ETL with multiple external API sources (not needed for single GOES satellite source)",
    default_args=default_args,
    schedule=None,                       # DISABLED - was '*/5 * * * *'
    catchup=False,
    is_paused_upon_creation=True,        # Start paused
    tags=["disabled", "multi-source", "apis"]
) as dag:

    # Extracción de datos de APIs
    crypto_task = PythonOperator(
        task_id="extract_crypto_prices",
        python_callable=extract_crypto_prices
    )
    
    weather_task = PythonOperator(
        task_id="extract_weather_data",
        python_callable=extract_weather_data
    )
    
    stocks_task = PythonOperator(
        task_id="extract_stock_prices",
        python_callable=extract_stock_prices
    )
    
    # Procesamiento de archivos
    csv_task = PythonOperator(
        task_id="process_csv_files",
        python_callable=process_csv_files
    )
    
    # Ejecutar todas las tareas en paralelo
    # Cambiar a una sola
    [crypto_task, weather_task, stocks_task, csv_task]
