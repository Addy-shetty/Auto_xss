# SecureScope Deployment Guide

## Overview

SecureScope is an enterprise-grade SECops platform for automated vulnerability discovery and management. This guide covers deployment options from development to production enterprise environments.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Web Dashboard │    │   Mobile App    │
│   (Nginx/ALB)   │    │   (React/Vue)   │    │   (Optional)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   API Gateway   │
                    │   (Kong/AWS)    │
                    └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scan Engine   │    │   API Service   │    │  Notification   │
│   (Python/Go)   │    │   (FastAPI)     │    │   Service       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │  Elasticsearch  │
│   (Primary DB)  │    │   (Cache/Queue) │    │   (Analytics)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Deployment Options

### 1. Development Environment

#### Quick Start with Docker Compose

```bash
# Clone the repository
git clone https://github.com/yourusername/securescope.git
cd securescope

# Copy environment configuration
cp .env.example .env

# Start the platform
docker-compose up -d

# Access the services
# API: http://localhost:8000
# Dashboard: http://localhost (when implemented)
# Flower (Celery Monitor): http://localhost:5555/flower
# Grafana: http://localhost:3000 (admin/admin)
# Kibana: http://localhost:5601
```

#### Local Development Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Go and security tools
./Install_tools.sh

# Set up database
docker-compose up -d postgres redis
export DATABASE_URL="postgresql://secureuser:securepass@localhost:5432/securescope"

# Run database migrations
alembic upgrade head

# Start the API server
python src/api/main.py

# Start Celery worker (in another terminal)
celery -A src.core.celery worker --loglevel=info

# Start Celery beat scheduler (in another terminal)
celery -A src.core.celery beat --loglevel=info
```

### 2. Production Deployment

#### Kubernetes Deployment

##### Prerequisites
- Kubernetes cluster (1.20+)
- Helm 3.x
- kubectl configured
- Persistent storage provider
- Load balancer (NGINX, ALB, etc.)

##### Helm Installation

```bash
# Add SecureScope Helm repository
helm repo add securescope https://charts.securescope.com
helm repo update

# Install with default values
helm install securescope securescope/securescope

# Install with custom values
helm install securescope securescope/securescope -f values-production.yaml
```

##### Custom Values Example (values-production.yaml)

```yaml
image:
  repository: securescope/api
  tag: "1.0.0"
  pullPolicy: IfNotPresent

replicaCount: 3

service:
  type: LoadBalancer
  port: 80

ingress:
  enabled: true
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: securescope.yourdomain.com
      paths: ["/"]
  tls:
    - secretName: securescope-tls
      hosts: ["securescope.yourdomain.com"]

postgresql:
  enabled: true
  auth:
    postgresPassword: "your-secure-password"
    database: "securescope"
  primary:
    persistence:
      enabled: true
      size: 100Gi

redis:
  enabled: true
  auth:
    enabled: true
    password: "your-redis-password"
  master:
    persistence:
      enabled: true
      size: 10Gi

elasticsearch:
  enabled: true
  replicas: 3
  minimumMasterNodes: 2
  volumeClaimTemplate:
    accessModes: ["ReadWriteOnce"]
    resources:
      requests:
        storage: 100Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi
```

#### AWS EKS Deployment

```bash
# Create EKS cluster
eksctl create cluster --name securescope-prod --region us-west-2 --nodes 3 --node-type m5.xlarge

# Install AWS Load Balancer Controller
kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller//crds?ref=master"

# Add EBS CSI driver for persistent storage
kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=master"

# Deploy SecureScope
helm install securescope securescope/securescope -f values-aws.yaml
```

#### Azure AKS Deployment

```bash
# Create AKS cluster
az aks create --resource-group securescope-rg --name securescope-prod --node-count 3 --node-vm-size Standard_D4s_v3 --enable-addons monitoring

# Get credentials
az aks get-credentials --resource-group securescope-rg --name securescope-prod

# Deploy SecureScope
helm install securescope securescope/securescope -f values-azure.yaml
```

#### Google GKE Deployment

```bash
# Create GKE cluster
gcloud container clusters create securescope-prod --zone us-central1-a --num-nodes 3 --machine-type n1-standard-4

# Deploy SecureScope
helm install securescope securescope/securescope -f values-gcp.yaml
```

### 3. On-Premises Deployment

#### Hardware Requirements

**Minimum Requirements (Small Deployment)**
- CPU: 8 cores
- RAM: 16 GB
- Storage: 100 GB SSD
- Network: 1 Gbps
- OS: Ubuntu 20.04 LTS or RHEL 8

**Recommended Requirements (Medium Deployment)**
- CPU: 16 cores
- RAM: 32 GB
- Storage: 500 GB SSD
- Network: 10 Gbps
- OS: Ubuntu 20.04 LTS or RHEL 8

**Enterprise Requirements (Large Deployment)**
- CPU: 32+ cores
- RAM: 64+ GB
- Storage: 1+ TB NVMe SSD
- Network: 10+ Gbps
- OS: Ubuntu 20.04 LTS or RHEL 8

#### Installation Steps

1. **Prepare the Environment**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. **Deploy SecureScope**

```bash
# Clone and configure
git clone https://github.com/yourusername/securescope.git
cd securescope
cp .env.example .env

# Edit configuration
vim .env
vim docker-compose.prod.yml

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

3. **Configure SSL/TLS**

```bash
# Generate SSL certificates (Let's Encrypt)
sudo apt install certbot
sudo certbot certonly --standalone -d securescope.yourdomain.com

# Copy certificates to nginx directory
sudo cp /etc/letsencrypt/live/securescope.yourdomain.com/fullchain.pem docker/nginx/ssl/
sudo cp /etc/letsencrypt/live/securescope.yourdomain.com/privkey.pem docker/nginx/ssl/

# Restart nginx
docker-compose restart nginx
```

## Configuration Management

### Environment Variables

```bash
# Core Application
APP_NAME=SecureScope
ENVIRONMENT=production
SECRET_KEY=your-super-secret-key-change-this
DEBUG=false

# Database
DATABASE_URL=postgresql://user:password@host:5432/database
DB_POOL_SIZE=20

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0

# Security
JWT_SECRET_KEY=your-jwt-secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# External Services
SMTP_SERVER=smtp.yourdomain.com
SMTP_PORT=587
SMTP_USERNAME=noreply@yourdomain.com
SMTP_PASSWORD=your-smtp-password

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=your-grafana-password

# Storage
S3_BUCKET=securescope-backups
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
```

### SSL/TLS Configuration

#### Self-Signed Certificates (Development)

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/nginx/ssl/nginx-selfsigned.key \
  -out docker/nginx/ssl/nginx-selfsigned.crt
```

#### Let's Encrypt (Production)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d securescope.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## High Availability Setup

### Database High Availability

#### PostgreSQL Streaming Replication

```yaml
# Primary database
postgresql-primary:
  image: postgres:15
  environment:
    POSTGRES_REPLICATION_USER: replicator
    POSTGRES_REPLICATION_PASSWORD: replicator_password
  volumes:
    - ./postgres/primary.conf:/etc/postgresql/postgresql.conf

# Replica databases
postgresql-replica-1:
  image: postgres:15
  environment:
    PGUSER: postgres
    POSTGRES_MASTER_SERVICE: postgresql-primary
    POSTGRES_REPLICATION_USER: replicator
    POSTGRES_REPLICATION_PASSWORD: replicator_password
  command: |
    bash -c "
    until pg_basebackup --pgdata=/var/lib/postgresql/data -R --slot=replication_slot --host=postgresql-primary --port=5432
    do
      echo 'Waiting for primary to connect...'
      sleep 1s
    done
    echo 'Backup done, starting replica...'
    postgres
    "
```

#### Redis Cluster

```yaml
redis-cluster:
  image: redis:7-alpine
  command: redis-cli --cluster create 
    redis-node-1:6379 redis-node-2:6379 redis-node-3:6379 
    redis-node-4:6379 redis-node-5:6379 redis-node-6:6379 
    --cluster-replicas 1 --cluster-yes
```

### Load Balancer Configuration

#### NGINX Load Balancer

```nginx
upstream api_backend {
    least_conn;
    server api-1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server api-2:8000 weight=1 max_fails=3 fail_timeout=30s;
    server api-3:8000 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name securescope.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Health check
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }
}
```

#### AWS Application Load Balancer

```json
{
  "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
  "Properties": {
    "Name": "securescope-alb",
    "Scheme": "internet-facing",
    "Type": "application",
    "SecurityGroups": ["sg-12345678"],
    "Subnets": ["subnet-12345678", "subnet-87654321"],
    "Tags": [
      {
        "Key": "Environment",
        "Value": "production"
      }
    ]
  }
}
```

## Monitoring & Observability

### Prometheus Metrics

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'securescope-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    
  - job_name: 'postgresql'
    static_configs:
      - targets: ['postgres-exporter:9187']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Grafana Dashboards

Key metrics to monitor:
- API response time and throughput
- Database connection pool usage
- Redis memory usage and hit rate
- Celery task queue length and processing time
- System resources (CPU, memory, disk)
- Security scan completion rates
- Vulnerability discovery trends

### Log Management

#### ELK Stack Configuration

```yaml
# Elasticsearch
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  environment:
    - cluster.name=securescope-logs
    - discovery.type=single-node
    - "ES_JAVA_OPTS=-Xms2g -Xmx2g"

# Logstash
logstash:
  image: docker.elastic.co/logstash/logstash:8.11.0
  volumes:
    - ./logstash/pipeline:/usr/share/logstash/pipeline

# Kibana
kibana:
  image: docker.elastic.co/kibana/kibana:8.11.0
  environment:
    - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
```

## Backup & Recovery

### Database Backup

```bash
#!/bin/bash
# backup-database.sh

BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="securescope"

# Create backup
pg_dump -h postgres -U secureuser -d $DB_NAME | gzip > "$BACKUP_DIR/securescope_${DATE}.sql.gz"

# Upload to S3 (optional)
aws s3 cp "$BACKUP_DIR/securescope_${DATE}.sql.gz" s3://securescope-backups/database/

# Clean old backups (keep last 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

### Application Data Backup

```bash
#!/bin/bash
# backup-application.sh

BACKUP_DIR="/backups/application"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup configuration
tar -czf "$BACKUP_DIR/config_${DATE}.tar.gz" /app/config

# Backup scan results
tar -czf "$BACKUP_DIR/results_${DATE}.tar.gz" /app/results

# Upload to S3
aws s3 sync $BACKUP_DIR s3://securescope-backups/application/
```

### Disaster Recovery

1. **Recovery Time Objective (RTO)**: 2 hours
2. **Recovery Point Objective (RPO)**: 1 hour
3. **Backup Frequency**: Every 6 hours
4. **Geographic Redundancy**: Multi-region backups

## Security Considerations

### Network Security

1. **Firewall Rules**
   - Only expose necessary ports (80, 443)
   - Restrict database access to application servers only
   - Use VPN for administrative access

2. **SSL/TLS Configuration**
   - Use TLS 1.3 or higher
   - Strong cipher suites only
   - HSTS headers enabled

3. **Container Security**
   - Regular image updates
   - Vulnerability scanning
   - Non-root user execution
   - Resource limits

### Application Security

1. **Authentication & Authorization**
   - Multi-factor authentication
   - Role-based access control
   - API key management
   - Session timeout

2. **Data Protection**
   - Encryption at rest
   - Encryption in transit
   - Secrets management (Vault)
   - Data anonymization

3. **Audit & Compliance**
   - Comprehensive audit logging
   - Regular security assessments
   - Compliance reporting (SOC2, ISO27001)
   - Incident response procedures

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check database connectivity
   docker exec -it postgres psql -U secureuser -d securescope -c "SELECT 1;"
   
   # Check connection pool
   docker logs api | grep "database"
   ```

2. **Redis Connection Issues**
   ```bash
   # Test Redis connectivity
   docker exec -it redis redis-cli ping
   
   # Check memory usage
   docker exec -it redis redis-cli info memory
   ```

3. **Celery Task Issues**
   ```bash
   # Check worker status
   docker exec -it worker celery -A src.core.celery inspect active
   
   # Check task queue
   docker exec -it worker celery -A src.core.celery inspect reserved
   ```

4. **Scan Tool Issues**
   ```bash
   # Test individual tools
   docker exec -it api subfinder -version
   docker exec -it api httpx -version
   docker exec -it api dalfox version
   ```

### Performance Tuning

1. **Database Optimization**
   - Connection pooling
   - Query optimization
   - Index tuning
   - Partition large tables

2. **Redis Optimization**
   - Memory management
   - Persistence configuration
   - Cluster setup for scale

3. **Application Optimization**
   - Async processing
   - Caching strategies
   - Resource limits
   - Load balancing

## Support & Maintenance

### Regular Maintenance Tasks

1. **Daily**
   - Monitor system health
   - Check backup status
   - Review security alerts

2. **Weekly**
   - Update security tools
   - Review scan results
   - Performance analysis

3. **Monthly**
   - Security patches
   - Database maintenance
   - Capacity planning

### Getting Support

- **Documentation**: https://docs.securescope.com
- **Community Forum**: https://community.securescope.com
- **GitHub Issues**: https://github.com/yourusername/securescope/issues
- **Enterprise Support**: support@securescope.com
- **Security Issues**: security@securescope.com