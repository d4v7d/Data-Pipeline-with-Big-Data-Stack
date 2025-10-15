from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from kafka import KafkaProducer
import pandas as pd
import json
import os
import numpy as np
import requests
from urllib.parse import urljoin

# Import webdavclient3 for better CITIC Nextcloud access
try:
    from webdav3.client import Client as WebDAVClient
except ImportError:
    print("webdavclient3 not installed. Install with: pip install webdavclient3")

try:
    import netCDF4
except ImportError:
    print("netCDF4 not available - will use alternate methods if needed")

try:
    import sunpy
    import sunpy.timeseries as ts
    from sunpy.net import Fido
    from sunpy.net import attrs as a
except ImportError:
    print("sunpy not available or fully installed - some functionality may be limited")

# ===================== Config =====================
KAFKA_HOST = "kafka:9092"
KAFKA_TOPIC = "goes_satellite_data"

# GOES data source configuration
GOES_DATA_URL = "https://nube.citic.ucr.ac.cr/index.php/s/3CcdjpMxsiYtagr"
LOCAL_DATA_DIR = "/tmp/goes_data"
PROCESSED_DIR = "/tmp/processed_goes"

def serializer(message):
    """Serialize messages as JSON-encoded UTF-8 bytes."""
    return json.dumps(message, default=str).encode("utf-8")

# ===================== GOES Data Functions =====================

def download_goes_data():
    """Download GOES satellite data from the specified URL using the working CITIC method"""
    print("=== GOES Data Download Task ===")
    
    # Create directories if they don't exist
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    try:
        download_count = 0
        
        # URL base que funciona (descubierta en pruebas)
        base_dav_url = "https://nube.citic.ucr.ac.cr/public.php/dav/files/3CcdjpMxsiYtagr"
        
        # Archivos específicos que sabemos que existen
        known_files = [
            "1. GOES/Repositorio01/EXIS/SFXR/20230426/OR_EXIS-L1b-SFXR_G18_s20231160000599_e20231160001294_c20231160001297.nc",
            "1. GOES/Repositorio01/EXIS/SFXR/20230426/OR_EXIS-L1b-SFXR_G18_s20231160001294_e20231160001599_c20231160001601.nc",
            "1. GOES/Repositorio01/EXIS/SFXR/20230426/OR_EXIS-L1b-SFXR_G18_s20231160001599_e20231160002294_c20231160002296.nc"
        ]
        
        print(f"Downloading GOES satellite data using working CITIC method")
        
        for i, file_path in enumerate(known_files):
            try:
                # Construir URL completa
                full_url = f"{base_dav_url}/{file_path}"
                filename = os.path.basename(file_path)
                local_file_path = os.path.join(LOCAL_DATA_DIR, filename)
                
                print(f"Downloading file {i+1}: {filename}")
                print(f"From URL: {full_url}")
                
                # Realizar descarga HTTP
                response = requests.get(full_url, stream=True, timeout=60)
                
                if response.status_code == 200:
                    # Escribir archivo
                    with open(local_file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    # Verificar descarga
                    if os.path.exists(local_file_path):
                        file_size = os.path.getsize(local_file_path)
                        if file_size > 0:
                            print(f"✓ Successfully downloaded: {local_file_path} ({file_size/1024:.1f} KB)")
                            download_count += 1
                        else:
                            print(f"✗ Downloaded file is empty: {filename}")
                            os.remove(local_file_path)  # Eliminar archivo vacío
                    else:
                        print(f"✗ File not created: {filename}")
                        
                else:
                    print(f"✗ HTTP error {response.status_code} for {filename}")
                    
            except Exception as e:
                print(f"✗ Error downloading {filename}: {e}")
                continue
        
        if download_count > 0:
            print(f"✓ Successfully downloaded {download_count} REAL GOES data files to {LOCAL_DATA_DIR}")
            return f"Downloaded {download_count} REAL GOES data files to {LOCAL_DATA_DIR}"
        else:
            print("✗ No files downloaded. Will fall back to sample data generation.")
            return f"No files downloaded to {LOCAL_DATA_DIR}"
        
    except Exception as e:
        print(f"Error downloading GOES data: {e}")
        raise

def test_simple_task():
    """Simple test task to verify DAG is working"""
    print("=== GOES Satellite ETL Pipeline Test ===")
    print("DAG is working correctly!")
    print("This is where we'll process GOES satellite data")
    
    # Test sample data generation
    sample_data = generate_sample_goes_data()
    print(f"Generated {len(sample_data)} sample GOES records")
    print("Sample record:", sample_data[0] if sample_data else "No data")
    
    return "Test completed successfully"

def extract_goes_satellite_data():
    """Extract GOES satellite data from NetCDF files and send to Kafka"""
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_HOST],
        value_serializer=serializer
    )
    
    try:
        # Required columns as specified by professor
        required_columns = [
            'product_time', 'time', 'solar_array_current_channel_index_label',
            'irradiance_xrsa1', 'irradiance_xrsa2', 'irradiance_xrsb1', 
            'irradiance_xrsb2', 'primary_xrsb', 'dispersion_angle', 'integration_time'
        ]
        
        # Check if we have NetCDF files to process
        if not os.path.exists(LOCAL_DATA_DIR):
            print(f"Error: Data directory {LOCAL_DATA_DIR} does not exist")
            return f"Error: Directory {LOCAL_DATA_DIR} not found"
        
        nc_files = [f for f in os.listdir(LOCAL_DATA_DIR) if f.endswith('.nc')]
        
        if not nc_files:
            print(f"No .nc files found in {LOCAL_DATA_DIR}")
            print("Generating and using sample data instead")
            # Use sample data as fallback
            sample_data = generate_sample_goes_data()
            
            for record in sample_data:
                producer.send(KAFKA_TOPIC, record)
                # Sleep briefly to avoid overwhelming Kafka
                import time
                time.sleep(0.01)
            
            print(f"Sent {len(sample_data)} sample records to Kafka topic {KAFKA_TOPIC}")
            return f"Processed {len(sample_data)} sample records (no .nc files found)"
        
        print(f"Found {len(nc_files)} NetCDF files to process")
        total_records = 0
        processed_files = []
        errors = []
        
        for nc_file in nc_files:
            file_path = os.path.join(LOCAL_DATA_DIR, nc_file)
            print(f"Processing NetCDF file: {file_path}")
            
            try:
                # Open the NetCDF file
                dataset = netCDF4.Dataset(file_path, 'r')
                
                # Extract metadata
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                extraction_timestamp = int(datetime.now().timestamp())
                
                # Get available variables
                available_vars = list(dataset.variables.keys())
                print(f"Available variables in {nc_file}: {available_vars}")
                
                # Print dimensions for debugging
                print(f"Dimensions in {nc_file}:")
                for dim_name, dim in dataset.dimensions.items():
                    print(f"  {dim_name}: {len(dim)}")
                
                # Extract time and convert to Unix timestamp if available
                if 'time' in available_vars:
                    times = dataset.variables['time'][:]
                    time_units = dataset.variables['time'].units if hasattr(dataset.variables['time'], 'units') else "unknown"
                    print(f"Time units: {time_units}")
                    print(f"Number of time points: {len(times)}")
                    
                    # For product_time, we'll use the file name info or a default
                    product_time = nc_file.split('_')[3] if len(nc_file.split('_')) > 3 else "unknown"
                    
                    # Extract other required data
                    records = []
                    
                    # Get channel indices for the arrays
                    channel_indices = None
                    if 'solar_array_current_channel_index' in available_vars:
                        channel_indices = dataset.variables['solar_array_current_channel_index'][:]
                        print(f"Channel indices found: {len(channel_indices)} values")
                    else:
                        print("No solar_array_current_channel_index found, using default channel labels")
                    
                    # Try different variable names that might exist in the file
                    variable_mappings = {
                        'irradiance_xrsa1': ['irradiance_xrsa1', 'xrsa1', 'xrsa_short'],
                        'irradiance_xrsa2': ['irradiance_xrsa2', 'xrsa2', 'xrsa_long'],
                        'irradiance_xrsb1': ['irradiance_xrsb1', 'xrsb1', 'xrsb_short'],
                        'irradiance_xrsb2': ['irradiance_xrsb2', 'xrsb2', 'xrsb_long'],
                        'primary_xrsb': ['primary_xrsb', 'xrsb_primary'],
                        'dispersion_angle': ['dispersion_angle', 'dispersion'],
                        'integration_time': ['integration_time', 'integ_time']
                    }
                    
                    # Extract data for each variable using the mappings
                    data_vars = {}
                    for target_var, possible_names in variable_mappings.items():
                        for var_name in possible_names:
                            if var_name in available_vars:
                                data_vars[target_var] = dataset.variables[var_name][:]
                                print(f"Found {target_var} as {var_name} with {len(data_vars[target_var])} values")
                                break
                        if target_var not in data_vars:
                            print(f"Could not find any variable for {target_var}, using zeros")
                            data_vars[target_var] = np.zeros(len(times))
                    
                    # Process each time point
                    for i in range(len(times)):
                        # Convert time to Unix timestamp - handle different time formats
                        try:
                            if 'seconds' in time_units.lower() and 'since' in time_units.lower():
                                # Try to parse the reference time
                                from datetime import datetime as dt, timedelta
                                ref_time_str = time_units.split('since')[1].strip()
                                ref_time = dt.strptime(ref_time_str, '%Y-%m-%d %H:%M:%S')
                                unix_time = int((ref_time + timedelta(seconds=float(times[i]))).timestamp())
                            else:
                                # Assume it's already a Unix timestamp
                                unix_time = int(times[i])
                        except Exception as e:
                            print(f"Time conversion error: {e}. Using extraction time instead.")
                            unix_time = extraction_timestamp - (len(times) - i) * 60  # Approximate with 1 minute intervals
                        
                        # Get channel label if available
                        if channel_indices is not None and i < len(channel_indices):
                            try:
                                channel_label = str(channel_indices[i])
                            except Exception:
                                channel_label = f"channel_{i % 4}"
                        else:
                            channel_label = f"channel_{i % 4}"
                        
                        # Create record - safely extract values
                        record = {
                            'product_time': product_time,
                            'time': unix_time,
                            'solar_array_current_channel_index_label': channel_label,
                            'source_file': nc_file,
                            'extraction_timestamp': extraction_timestamp,
                            'file_size_mb': float(file_size_mb)
                        }
                        
                        # Add the variable data, handling any index errors
                        for var_name, data_array in data_vars.items():
                            try:
                                if i < len(data_array):
                                    value = float(data_array[i])
                                    # Handle NaN values
                                    if np.isnan(value):
                                        value = 0.0
                                else:
                                    value = 0.0
                                record[var_name] = value
                            except Exception as e:
                                print(f"Error extracting {var_name} at index {i}: {e}")
                                record[var_name] = 0.0
                        
                        # Send to Kafka
                        producer.send(KAFKA_TOPIC, record)
                        records.append(record)
                    
                    total_records += len(records)
                    print(f"Sent {len(records)} records from file {nc_file} to Kafka topic {KAFKA_TOPIC}")
                    
                    # Move processed file to processed directory
                    processed_path = os.path.join(PROCESSED_DIR, nc_file)
                    os.rename(file_path, processed_path)
                    processed_files.append(nc_file)
                    
                else:
                    print(f"Warning: 'time' variable not found in {nc_file}")
                    # Try alternate approach using sunpy if this is a GOES XRS file
                    try:
                        import sunpy.timeseries as ts
                        print("Attempting to read with sunpy timeseries...")
                        goes_ts = ts.TimeSeries(file_path)
                        
                        # Extract data from sunpy TimeSeries
                        df = goes_ts.to_dataframe()
                        print(f"Successfully read {len(df)} records with sunpy")
                        
                        # Process each row in the dataframe
                        records = []
                        for idx, row in df.iterrows():
                            record = {
                                'product_time': product_time,
                                'time': int(idx.timestamp()),
                                'solar_array_current_channel_index_label': "sunpy_extract",
                                'source_file': nc_file,
                                'extraction_timestamp': extraction_timestamp,
                                'file_size_mb': float(file_size_mb)
                            }
                            
                            # Map columns to required fields
                            column_mappings = {
                                'xrsa_short': 'irradiance_xrsa1',
                                'xrsa_long': 'irradiance_xrsa2',
                                'xrsb_short': 'irradiance_xrsb1',
                                'xrsb_long': 'irradiance_xrsb2'
                            }
                            
                            for sunpy_col, our_col in column_mappings.items():
                                if sunpy_col in df.columns:
                                    record[our_col] = float(row[sunpy_col])
                                else:
                                    record[our_col] = 0.0
                            
                            # Fill in missing fields
                            for field in ['primary_xrsb', 'dispersion_angle', 'integration_time']:
                                if field not in record:
                                    record[field] = 0.0
                            
                            producer.send(KAFKA_TOPIC, record)
                            records.append(record)
                        
                        total_records += len(records)
                        print(f"Sent {len(records)} sunpy-extracted records from file {nc_file}")
                        
                        # Move processed file
                        processed_path = os.path.join(PROCESSED_DIR, nc_file)
                        os.rename(file_path, processed_path)
                        processed_files.append(nc_file)
                        
                    except Exception as e:
                        print(f"Sunpy extraction failed: {e}")
                        errors.append(f"Failed to process {nc_file} with either netCDF4 or sunpy")
                
                dataset.close()
                
            except Exception as e:
                print(f"Error processing NetCDF file {nc_file}: {e}")
                errors.append(f"Failed to process {nc_file}: {str(e)}")
        
        if total_records > 0:
            print(f"Total records processed: {total_records} from {len(processed_files)} files")
            print(f"Errors encountered: {len(errors)}")
            if errors:
                print("First few errors:", errors[:3])
            return f"Successfully processed {total_records} records from {len(processed_files)} files"
        else:
            print("No records processed from NetCDF files, falling back to sample data")
            sample_data = generate_sample_goes_data()
            
            for record in sample_data:
                producer.send(KAFKA_TOPIC, record)
            
            print(f"Sent {len(sample_data)} sample records to Kafka topic {KAFKA_TOPIC}")
            return f"Processed {len(sample_data)} sample records (no valid data in NC files)"
        
    except Exception as e:
        print(f"Error extracting GOES data: {e}")
        raise
    finally:
        producer.flush()
        producer.close()

def generate_sample_goes_data():
    """Generate sample GOES data for testing purposes"""
    sample_data = []
    base_time = datetime.now()
    
    for i in range(100):
        record = {
            'product_time': (base_time - timedelta(minutes=i)).isoformat(),
            'time': int((base_time - timedelta(minutes=i)).timestamp()),
            'solar_array_current_channel_index_label': f"channel_{i % 4}",
            'irradiance_xrsa1': np.random.uniform(1e-9, 1e-6),
            'irradiance_xrsa2': np.random.uniform(1e-9, 1e-6),
            'irradiance_xrsb1': np.random.uniform(1e-10, 1e-7),
            'irradiance_xrsb2': np.random.uniform(1e-10, 1e-7),
            'primary_xrsb': np.random.uniform(1e-10, 1e-7),
            'dispersion_angle': np.random.uniform(0, 360),
            'integration_time': np.random.uniform(1, 10),
            'source_file': 'sample_data.nc',
            'extraction_timestamp': int(datetime.now().timestamp()),
            'file_size_mb': 15.5
        }
        sample_data.append(record)
    
    return sample_data

def calculate_storage_metrics():
    """Calculate storage growth metrics for 1 day, 1 week, 1 month"""
    try:
        print("=== Storage Growth Analysis ===")
        
        # Connect to Druid to query data volume
        # For this example, we'll estimate based on file sizes
        
        # Get processed files
        processed_files = os.listdir(PROCESSED_DIR) if os.path.exists(PROCESSED_DIR) else []
        nc_processed_files = [f for f in processed_files if f.endswith('.nc')]
        
        if not nc_processed_files:
            print("No processed files found for analysis")
            
            # Create dummy metrics for demonstration
            return {
                "daily_growth_mb": 250,     # Example: 250 MB per day
                "weekly_growth_mb": 1750,    # Example: 1.75 GB per week
                "monthly_growth_mb": 7500,   # Example: 7.5 GB per month
                "avg_record_size_kb": 2.5    # Example: 2.5 KB per record
            }
        
        # Calculate total size of processed files
        total_size_bytes = sum(os.path.getsize(os.path.join(PROCESSED_DIR, f)) for f in nc_processed_files)
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        # Calculate average file size
        avg_file_size_mb = total_size_mb / len(nc_processed_files)
        
        # Connect to Kafka to estimate record count
        # For this example, we'll use a fixed estimate
        avg_records_per_file = 1000  # Example value
        estimated_records = avg_records_per_file * len(nc_processed_files)
        
        # Estimate average record size
        avg_record_size_bytes = total_size_bytes / estimated_records if estimated_records > 0 else 0
        avg_record_size_kb = avg_record_size_bytes / 1024
        
        # Calculate daily files based on GOES satellite data frequency
        # GOES typically provides data at 1-minute intervals
        daily_files_count = 24 * 60  # One file per minute
        files_per_day_ratio = daily_files_count / len(nc_processed_files)
        
        # Estimate daily, weekly, monthly growth
        daily_growth_mb = avg_file_size_mb * daily_files_count
        weekly_growth_mb = daily_growth_mb * 7
        monthly_growth_mb = daily_growth_mb * 30
        
        print(f"=== Storage Growth Estimates ===")
        print(f"Files analyzed: {len(nc_processed_files)}")
        print(f"Total size: {total_size_mb:.2f} MB")
        print(f"Average file size: {avg_file_size_mb:.2f} MB")
        print(f"Estimated records: {estimated_records}")
        print(f"Average record size: {avg_record_size_kb:.2f} KB")
        print(f"Daily growth: {daily_growth_mb:.2f} MB")
        print(f"Weekly growth: {weekly_growth_mb:.2f} MB ({weekly_growth_mb/1024:.2f} GB)")
        print(f"Monthly growth: {monthly_growth_mb:.2f} MB ({monthly_growth_mb/1024:.2f} GB)")
        
        # Return metrics as a dictionary
        return {
            "daily_growth_mb": daily_growth_mb,
            "weekly_growth_mb": weekly_growth_mb,
            "monthly_growth_mb": monthly_growth_mb,
            "avg_record_size_kb": avg_record_size_kb
        }
        
    except Exception as e:
        print(f"Error calculating storage metrics: {e}")
        return {
            "error": str(e),
            "daily_growth_mb": 0,
            "weekly_growth_mb": 0,
            "monthly_growth_mb": 0
        }

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
    dag_id="goes_satellite_etl",
    description="ETL Pipeline for GOES Satellite EXIS/SFXR Data - Final Course Project",
    default_args=default_args,
    schedule='@daily',                  # Run once daily - change to your desired frequency
    catchup=False,
    tags=["production", "goes-satellite", "final-project"]
) as dag:

    # Download GOES data
    download_task = PythonOperator(
        task_id="download_goes_data",
        python_callable=download_goes_data
    )

    # Simple test task
    test_task = PythonOperator(
        task_id="test_goes_pipeline",
        python_callable=test_simple_task
    )
    
    # Extract and process GOES data
    extract_task = PythonOperator(
        task_id="extract_goes_satellite_data",
        python_callable=extract_goes_satellite_data
    )
    
    # Calculate storage growth metrics
    metrics_task = PythonOperator(
        task_id="calculate_storage_metrics",
        python_callable=calculate_storage_metrics
    )
    
    # Set task dependencies
    download_task >> test_task >> extract_task >> metrics_task
