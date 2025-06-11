# Docker Setup Guide for Lead Generation System

This guide explains how to run the DPC Health Insurance Lead Generation System using Docker containers.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 8GB RAM available for containers
- 20GB disk space for volumes and images

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd lead-generation-system
   ```

2. **Configure Environment**
   ```bash
   # Copy the Docker environment template
   cp .env.docker .env
   
   # Edit .env with your actual API keys and settings
   nano .env
   ```

3. **Build and Start Core Services**
   ```bash
   # Start database, Redis, and RabbitMQ
   docker-compose up -d postgres redis rabbitmq
   
   # Wait for services to be healthy (30-60 seconds)
   docker-compose ps
   ```

4. **Initialize Database**
   ```bash
   # Run database initialization
   docker-compose --profile setup up db-init
   ```

5. **Start Application and Workers**
   ```bash
   # Start all application services
   docker-compose up -d app enrichment-worker scoring-worker crm-sync-worker
   ```

## Available Services

### Core Services
- **PostgreSQL** (`postgres:5432`) - Main database
- **Redis** (`redis:6379`) - Caching and session storage  
- **RabbitMQ** (`rabbitmq:5672`, Management UI: `15672`) - Message queue
- **Application** (`app:8000`) - Main application service
- **Workers** - Background processing services

### Management Tools (Optional)
- **pgAdmin** (`localhost:5050`) - Database management
  - Email: `admin@example.com`
  - Password: `admin`
- **Redis Commander** (`localhost:8081`) - Redis management
- **RabbitMQ Management** (`localhost:15672`) - Queue management
  - Username: `admin`
  - Password: `admin`

### Monitoring (Optional)
- **Prometheus** (`localhost:9091`) - Metrics collection
- **Grafana** (`localhost:3000`) - Metrics visualization
  - Username: `admin`
  - Password: `admin`

## Usage Commands

### Start Services with Profiles

```bash
# Core services only
docker-compose up -d

# Include management tools
docker-compose --profile tools up -d

# Include monitoring
docker-compose --profile monitoring up -d

# Include scrapers
docker-compose --profile scrapers up -d

# All services
docker-compose --profile tools --profile monitoring --profile scrapers up -d
```

### Database Operations

```bash
# Initialize database schema
docker-compose --profile setup up db-init

# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d lead_generation

# Backup database
docker-compose exec postgres pg_dump -U postgres -d lead_generation > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres -d lead_generation < backup.sql
```

### Application Operations

```bash
# View application logs
docker-compose logs -f app

# Run scrapers
docker-compose --profile scrapers up bls-scraper

# Execute CLI commands
docker-compose exec app python cli.py --help
docker-compose exec app python cli.py status
docker-compose exec app python cli.py scrape bls --states CA TX

# Scale workers
docker-compose up -d --scale enrichment-worker=3
```

### Monitoring and Debugging

```bash
# View all service status
docker-compose ps

# View logs for specific service
docker-compose logs -f enrichment-worker

# Enter container shell
docker-compose exec app bash

# Monitor resource usage
docker stats

# View worker queues in RabbitMQ Management UI
open http://localhost:15672
```

## Environment Configuration

### Required API Keys
Update `.env` file with your actual API keys:

```bash
# Government Data Sources
BLS_API_KEY=your_actual_bls_key
SAM_GOV_API_KEY=your_actual_sam_gov_key

# Enrichment Services  
APOLLO_API_KEY=your_actual_apollo_key
PROXYCURL_API_KEY=your_actual_proxycurl_key
DROPCONTACT_API_KEY=your_actual_dropcontact_key

# CRM Integration
PIPEDRIVE_API_KEY=your_actual_pipedrive_key
PIPEDRIVE_DOMAIN=yourcompany.pipedrive.com
```

### Database Configuration
The system uses PostgreSQL with the following default settings:
- Database: `lead_generation`
- Username: `postgres`
- Password: `postgres`
- Port: `5432`

### Queue Configuration
RabbitMQ is configured with:
- Default vhost: `/`
- Username: `admin`
- Password: `admin`
- Port: `5672`
- Management UI: `15672`

## Data Persistence

All important data is persisted in Docker volumes:
- `postgres_data` - Database files
- `redis_data` - Redis snapshots
- `rabbitmq_data` - Queue data
- `./logs` - Application logs
- `./results` - Scraping results
- `./data` - Application data

## Scaling and Production

### Horizontal Scaling
```bash
# Scale specific workers
docker-compose up -d --scale enrichment-worker=5 --scale scoring-worker=3

# Scale with different configurations
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Resource Limits
Add resource limits to docker-compose.yml:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Production Checklist
- [ ] Change all default passwords
- [ ] Use production-grade secret management
- [ ] Configure log rotation
- [ ] Set up automated backups
- [ ] Configure monitoring alerts
- [ ] Use Docker Swarm or Kubernetes for orchestration
- [ ] Configure reverse proxy (nginx/traefik)
- [ ] Set up SSL certificates

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check service health
   docker-compose ps
   
   # View detailed logs
   docker-compose logs <service-name>
   ```

2. **Database connection errors**
   ```bash
   # Check PostgreSQL is running
   docker-compose exec postgres pg_isready -U postgres
   
   # Test connection from app
   docker-compose exec app python -c "from config import get_settings; print(get_settings().database_url)"
   ```

3. **Worker not processing tasks**
   ```bash
   # Check RabbitMQ queues
   docker-compose exec rabbitmq rabbitmqctl list_queues
   
   # Check worker logs
   docker-compose logs -f enrichment-worker
   ```

4. **Out of memory errors**
   ```bash
   # Check container resource usage
   docker stats
   
   # Increase Docker daemon memory limits
   # Or reduce worker concurrency in environment variables
   ```

### Health Checks
All services include health checks. Use these commands to verify system health:

```bash
# Overall system health
docker-compose ps

# Individual service health
docker-compose exec app python -c "from config import get_settings; print('App OK')"
docker-compose exec postgres pg_isready -U postgres
docker-compose exec redis redis-cli ping
docker-compose exec rabbitmq rabbitmq-diagnostics ping
```

## Maintenance

### Regular Maintenance Tasks

```bash
# Clean up old containers and images
docker system prune -a

# Update base images
docker-compose pull
docker-compose build --no-cache

# Rotate logs
docker-compose exec app find /app/logs -name "*.log" -mtime +30 -delete

# Backup database
docker-compose exec postgres pg_dump -U postgres -d lead_generation | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Updates and Migrations

```bash
# Pull latest code
git pull

# Rebuild and restart services
docker-compose build
docker-compose up -d --force-recreate

# Run any new migrations
docker-compose exec app python cli.py upgrade-database
```

## Support

For issues and questions:
1. Check the logs: `docker-compose logs -f <service>`
2. Verify configuration: Check `.env` file settings
3. Review the main README.md for application-specific help
4. Check Docker and system resources: `docker system df`

## Security Notes

- Default passwords are used for development only
- In production, use secrets management (Docker secrets, HashiCorp Vault, etc.)
- Consider using Docker security scanning: `docker scan <image>`
- Regularly update base images for security patches
- Use network policies to restrict inter-container communication
- Enable Docker Content Trust in production environments