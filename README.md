# Real-Time Data Pipeline with Modern Big Data Stack

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-017CEE?style=for-the-badge&logo=Apache%20Airflow&logoColor=white)](https://airflow.apache.org/)
[![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-000?style=for-the-badge&logo=apachekafka)](https://kafka.apache.org/)
[![Apache Druid](https://img.shields.io/badge/Apache%20Druid-29F1FB?style=for-the-badge&logo=apachedruid&logoColor=black)](https://druid.apache.org/)
[![Apache Superset](https://img.shields.io/badge/Apache%20Superset-1FA8C9?style=for-the-badge&logo=apache-superset&logoColor=white)](https://superset.apache.org/)
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://www.python.org/)

## 🚀 Project Overview

A comprehensive real-time data pipeline implementation designed to process satellite data from GOES (Geostationary Operational Environmental Satellite) and financial market data. This project demonstrates enterprise-grade data engineering practices using modern open-source technologies for ingestion, processing, storage, and visualization of large-scale streaming data.

### 🎯 Key Features

- **Real-time Data Ingestion**: Automated download and processing of GOES satellite NetCDF files from CITIC (Universidad de Costa Rica)
- **Multi-source Data Integration**: Cryptocurrency prices, weather data, and satellite telemetry
- **Streaming Architecture**: High-throughput data pipeline using Apache Kafka
- **Analytical Storage**: Time-series optimized storage with Apache Druid
- **Interactive Dashboards**: Real-time visualization and monitoring with Apache Superset
- **Orchestration**: Workflow management and scheduling with Apache Airflow
- **Containerized Deployment**: Full stack deployment using Docker Compose

## 🏗️ Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    CITIC    │───▶│   Airflow    │───▶│    Kafka    │───▶│    Druid    │───▶│  Superset   │
│   NetCDF    │    │   (ETL/DAG)  │    │ (Streaming) │    │ (Storage)   │    │(Visualization)│
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
        │                  │                   │                   │                   │
        │                  ▼                   ▼                   ▼                   ▼
    External APIs     Workflow Mgmt      Message Queue      Analytics DB        BI & Dashboards
```

### Core Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Orchestration** | Apache Airflow | ETL workflow management, data scheduling |
| **Message Broker** | Apache Kafka | Real-time data streaming and event processing |
| **Analytics Database** | Apache Druid | High-performance time-series data storage |
| **Visualization** | Apache Superset | Interactive dashboards and data exploration |
| **Compute Engine** | Apache Spark | Large-scale data processing |
| **Database** | PostgreSQL | Metadata and configuration storage |
| **Caching** | Redis | Session management and caching |
| **Container Orchestration** | Docker Compose | Service deployment and management |

## 🛠️ Technology Stack

### Data Engineering
- **Apache Airflow** - Workflow orchestration and scheduling
- **Apache Kafka** - Distributed streaming platform
- **Apache Druid** - Real-time analytics database
- **Apache Spark** - Unified analytics engine for big data processing
- **Python** - Primary programming language with scientific computing libraries

### Data Sources
- **GOES Satellite Data** - EXIS/SFXR scientific datasets from CITIC repository
- **Cryptocurrency APIs** - Real-time market data from CoinGecko
- **Weather APIs** - Meteorological data from OpenWeatherMap
- **Financial Data** - Stock market and trading information

### Visualization & Analytics
- **Apache Superset** - Modern data visualization platform
- **SQL Analytics** - Advanced querying capabilities
- **Interactive Dashboards** - Real-time monitoring and reporting

### Infrastructure
- **Docker & Docker Compose** - Containerization and orchestration
- **PostgreSQL** - Relational database for metadata
- **Redis** - In-memory data structure store
- **Nginx** - Web server and reverse proxy (optional)

## 📦 Installation & Setup

### Prerequisites

- **Docker Desktop** (>= 20.0)
- **Docker Compose** (>= 2.0)
- **8GB RAM** minimum (16GB recommended)
- **20GB** free disk space
- **Python 3.8+** (for development/testing)

### Quick Start

1. **Clone the Repository**
   ```bash
   git clone https://github.com/d4v7d/Data-Pipeline-with-Big-Data-Stack.git
   ```

2. **Start the Pipeline**
   ```bash
   docker-compose up -d
   ```

3. **Verify Services**
   ```bash
   docker-compose ps
   ```

4. **Access Web Interfaces**
   - **Airflow**: http://localhost:3000 (admin/admin)
   - **Superset**: http://localhost:8088 (admin/admin)
   - **Druid Console**: http://localhost:8888
   - **Spark UI**: http://localhost:8080

### Service Configuration

| Service | Port | Default Credentials |
|---------|------|-------------------|
| Airflow | 3000 | admin / admin |
| Superset | 8088 | admin / admin |
| Druid Console | 8888 | - |
| Spark Master UI | 8080 | - |
| Kafka | 9092 | - |
| PostgreSQL | 5432 | druid / FoolishPassword |
| Redis | 6379 | - |

## 🔧 Usage Guide

### 1. Activate Data Pipelines

**GOES Satellite Data Pipeline:**
1. Access Airflow at http://localhost:3000
2. Enable the `goes_satellite_etl` DAG
3. Trigger manual execution
4. Monitor task progress and logs

**Real-time Financial Data:**
1. Enable the `real_data_etl` DAG
2. Configure API keys for external services
3. Monitor data ingestion in Kafka topics

### 2. Configure Data Sources

**Druid Datasources:**
```bash
# Copy pre-configured datasource specifications
- druid-goes-satellite-datasource.json
- druid-kafka-datasource.json
- druid-real-crypto-datasource.json
- druid-weather-datasource.json
```

**Kafka Topics:**
- `goes_satellite_data` - GOES EXIS/SFXR telemetry
- `real_crypto_prices` - Cryptocurrency market data
- `weather_data` - Meteorological information
- `stock_market_data` - Financial market data

### 3. Build Dashboards

**Connect Superset to Druid:**
1. Navigate to Data → Databases
2. Add new database connection:
   ```
   Database Type: Apache Druid
   SQLAlchemy URI: druid://router:8888/druid/v2/sql
   ```

**Create Visualizations:**
- Time Series Charts for satellite telemetry
- Real-time price tracking for cryptocurrencies
- Geographic weather maps
- Performance monitoring dashboards

### 4. Query Data

**Sample SQL Queries:**

```sql
-- GOES Satellite Data Analysis
SELECT 
    TIME_FLOOR(__time, 'PT1H') AS hour,
    AVG(irradiance_xrsa1) AS avg_xrsa1,
    AVG(irradiance_xrsa2) AS avg_xrsa2,
    COUNT(*) as data_points
FROM goes_satellite_datasource
WHERE __time >= CURRENT_TIMESTAMP - INTERVAL '24' HOUR
GROUP BY 1
ORDER BY 1;

-- Cryptocurrency Price Trends
SELECT 
    coin_id,
    price_usd,
    change_24h,
    market_cap
FROM real_crypto_prices
WHERE __time >= CURRENT_TIMESTAMP - INTERVAL '1' HOUR
ORDER BY market_cap DESC;
```

## 📊 Data Sources & Processing

### GOES Satellite Data (Primary Focus)
- **Source**: CITIC - Universidad de Costa Rica repository
- **Format**: NetCDF4 scientific data files
- **Content**: EXIS/SFXR solar irradiance measurements
- **Processing**: 30 records per file, 10-second intervals
- **Variables**: XRS-A/B irradiance, dispersion angles, integration times

### Financial Market Data
- **Cryptocurrencies**: Real-time prices from CoinGecko API
- **Weather Data**: OpenWeatherMap API integration
- **Stock Markets**: Financial data streaming (configurable)

### Data Processing Pipeline
1. **Extraction**: Automated download via Airflow DAGs
2. **Transformation**: Python-based data cleaning and enrichment
3. **Loading**: Real-time streaming to Kafka topics
4. **Storage**: Time-series optimized storage in Druid
5. **Visualization**: Interactive dashboards in Superset

## 🔍 Monitoring & Observability

### Pipeline Health Monitoring
- **Airflow DAG Status**: Task success/failure tracking
- **Kafka Topic Lag**: Message processing delays
- **Druid Ingestion**: Real-time data ingestion rates
- **System Resources**: Memory, CPU, and disk usage

### Data Quality Metrics
- **Record Counts**: Data volume validation
- **Timestamp Continuity**: Gap detection in time series
- **Data Freshness**: Latency monitoring
- **Error Rates**: Failed processing tracking

## 🚨 Troubleshooting

### Common Issues

**Services Won't Start:**
```bash
# Check Docker resources
docker system df
docker system prune -a

# Restart services
docker-compose down
docker-compose up -d
```

**Data Not Appearing in Druid:**
```bash
# Check Kafka topic data
docker exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic goes_satellite_data --from-beginning

# Verify Druid ingestion
curl http://localhost:8888/druid/indexer/v1/supervisor
```

**Connection Issues:**
```bash
# Test service connectivity
docker exec airflow curl http://kafka:9092
docker exec superset curl http://router:8888/status/health
```

### Log Analysis
```bash
# View service logs
docker-compose logs airflow
docker-compose logs druid
docker-compose logs kafka

# Follow real-time logs
docker-compose logs -f [service_name]
```

## 📈 Performance Metrics

### Throughput Capacity
- **Kafka**: 10,000+ messages/second
- **Druid**: 100,000+ events/second ingestion
- **Data Latency**: < 10 seconds end-to-end
- **Storage**: Petabyte-scale with automatic partitioning

### Resource Requirements
- **Minimum**: 8GB RAM, 4 CPU cores
- **Recommended**: 16GB RAM, 8 CPU cores
- **Storage**: 20GB+ for logs and data
- **Network**: High-bandwidth for external API calls

## 🔐 Security Considerations

### Authentication & Authorization
- Default credentials for development only
- Production deployment requires:
  - SSL/TLS encryption
  - API key management
  - User access controls
  - Network security policies

### Data Privacy
- Satellite data is public scientific information
- Financial data requires API compliance
- No PII or sensitive data processing

## 🧪 Testing

### Unit Tests
```bash
# Test individual components
python test_citic_download_v2.py
```

### Integration Tests
```bash
# Verify end-to-end pipeline
docker exec airflow airflow tasks test goes_satellite_etl download_goes_data 2025-07-01
```

### Data Validation
```bash
# Verify data quality
SELECT COUNT(*) FROM goes_satellite_datasource WHERE __time > CURRENT_TIMESTAMP - INTERVAL '1' HOUR;
```

## 🚀 Future Enhancements

### Planned Features
- **Auto-scaling**: Kubernetes deployment for cloud scaling
- **Stream Processing**: Apache Flink integration for complex event processing
- **Machine Learning**: Anomaly detection in satellite data
- **Data Lake**: S3/MinIO integration for long-term storage
- **API Gateway**: RESTful API for external data access

### Optimization Opportunities
- **Caching**: Redis-based query result caching
- **Compression**: Data compression for storage efficiency
- **Partitioning**: Intelligent data partitioning strategies
- **Monitoring**: Prometheus/Grafana integration

## 📚 Documentation

### Additional Resources
- [GOES Pipeline Report](GOES_PIPELINE_REPORT.md) - Detailed implementation documentation
- [Airflow DAGs](app_airflow/app/dags/) - ETL workflow definitions
- [Druid Configurations](druid-*-datasource.json) - Data source specifications
- [Docker Compose](docker-compose.yaml) - Service orchestration

### Academic Context
This project was developed as a comprehensive demonstration of modern data engineering practices, specifically focusing on real-time processing of scientific satellite data. It showcases industry-standard tools and methodologies for building scalable, maintainable data pipelines.

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **CITIC - Universidad de Costa Rica** for providing GOES satellite data
- **Apache Software Foundation** for the excellent open-source tools
- **Docker Community** for containerization platform
- **Scientific Computing Community** for Python libraries (NetCDF4, NumPy, Pandas)

## 📞 Contact

**David Gonzalez Villanueva**
- GitHub: [@d4v7d](https://github.com/d4v7d)
- LinkedIn: [David GV](www.linkedin.com/in/david-gonzález-villanueva-413969169)
- Email: davidgonzav2003@gmail.com

---