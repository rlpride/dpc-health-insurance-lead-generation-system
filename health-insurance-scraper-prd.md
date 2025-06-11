# Health Insurance Lead Generation System
## Product Requirements Document & Implementation Guide

---

## Table of Contents
1. [Product Requirements Document (PRD)](#product-requirements-document-prd)
2. [README - Quick Start Guide](#readme---quick-start-guide)
3. [Agent-Based Parallel Execution Strategy](#agent-based-parallel-execution-strategy)
4. [Implementation Lesson Plan](#implementation-lesson-plan)
5. [Cursor IDE Prompts](#cursor-ide-prompts)

---

## Product Requirements Document (PRD)

### 1. Product Overview

**Product Name:** DPC Health Insurance Lead Generation System  
**Version:** 1.0.0  
**Date:** June 2025  
**Product Owner:** [Your Name]  

### 2. Executive Summary

This system automates the identification and qualification of businesses with 50-1200 employees that are prime candidates for self-funded health insurance plans with Direct Primary Care (DPC). The system leverages public government data sources, enriches company information with decision-maker contacts, and integrates with existing B2B sales tools.

### 3. Problem Statement

**Current State:**
- Manual research requires 4-6 hours per 10 qualified leads
- Limited visibility into company size and industry classifications
- Difficulty identifying decision-makers within target companies
- No systematic approach to prioritizing outreach efforts

**Desired State:**
- Automated identification of 100+ qualified leads daily
- Enriched contact information for 3-5 decision-makers per company
- Integrated workflow with existing CRM and dialer systems
- Data-driven lead scoring based on industry and company characteristics

### 4. Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Lead Volume | 500+ qualified leads/week | System reporting |
| Data Accuracy | >85% verified companies | Manual validation sample |
| Contact Rate | >25% decision-maker reach | CRM tracking |
| Cost per Lead | <$5 fully enriched | Total costs / leads |
| System Uptime | >99% availability | Monitoring tools |

### 5. User Stories

**As a Sales Representative:**
- I want to receive a daily list of qualified companies with verified decision-maker contacts
- I want leads automatically added to my CRM with proper tags and scores
- I want to see why each lead was selected (industry, size, location)

**As a Sales Manager:**
- I want to monitor lead generation performance and quality metrics
- I want to adjust targeting parameters based on conversion data
- I want to ensure compliance with data collection regulations

**As a System Administrator:**
- I want to monitor API usage and costs across all data providers
- I want to receive alerts for system failures or data quality issues
- I want to easily add new data sources or enrichment providers

### 6. Functional Requirements

#### 6.1 Data Collection Module
- **FR-001:** Extract business data from BLS QCEW API with size classifications
- **FR-002:** Query SAM.gov Entity Management API for business details
- **FR-003:** Implement configurable rate limiting (2-10 second delays)
- **FR-004:** Store raw data with source attribution and timestamp

#### 6.2 Data Enrichment Module
- **FR-005:** Integrate with Apollo.io API for contact discovery
- **FR-006:** Support fallback to alternative providers (Proxycurl, Hunter.io)
- **FR-007:** Verify email addresses through Dropcontact or similar service
- **FR-008:** Calculate lead scores based on configurable industry weights

#### 6.3 CRM Integration Module
- **FR-009:** Create/update contacts in Pipedrive via REST API
- **FR-010:** Add custom fields for lead score, industry risk, employee range
- **FR-011:** Create deals for high-score leads (>80)
- **FR-012:** Log all interactions for compliance tracking

#### 6.4 Monitoring & Reporting
- **FR-013:** Real-time dashboard showing leads generated, API calls, costs
- **FR-014:** Daily email reports with key metrics and anomalies
- **FR-015:** Compliance audit trail for all data collection activities

### 7. Non-Functional Requirements

#### 7.1 Performance
- **NFR-001:** Process 1,000 companies per hour during peak operation
- **NFR-002:** API response time <2 seconds for enrichment calls
- **NFR-003:** Database queries return results in <500ms

#### 7.2 Scalability
- **NFR-004:** Support horizontal scaling to 10 concurrent scrapers
- **NFR-005:** Handle 100,000+ companies in database without degradation
- **NFR-006:** Queue system to manage 10,000+ enrichment requests

#### 7.3 Security & Compliance
- **NFR-007:** Encrypt all API keys and sensitive data at rest
- **NFR-008:** Implement rate limiting to respect source website policies
- **NFR-009:** Maintain opt-out list with immediate processing
- **NFR-010:** GDPR-compliant data retention policies (90 days)

### 8. Technical Architecture

```mermaid
graph TB
    A[Government Data Sources] --> B[Scrapy Collectors]
    B --> C[RabbitMQ Queue]
    C --> D[Enrichment Workers]
    D --> E[PostgreSQL Database]
    E --> F[Scoring Engine]
    F --> G[CRM Integration]
    F --> H[Monitoring Dashboard]
    
    I[Apollo.io API] --> D
    J[Dropcontact API] --> D
    K[Proxycurl API] --> D
```

### 9. Data Model

```sql
-- Core tables structure
CREATE TABLE companies (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    naics_code VARCHAR(6),
    employee_range VARCHAR(50),
    state VARCHAR(2),
    city VARCHAR(100),
    lead_score INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE contacts (
    id UUID PRIMARY KEY,
    company_id UUID REFERENCES companies(id),
    full_name VARCHAR(255),
    title VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    linkedin_url VARCHAR(255),
    verified BOOLEAN,
    created_at TIMESTAMP
);

CREATE TABLE scraping_logs (
    id UUID PRIMARY KEY,
    source VARCHAR(50),
    status VARCHAR(20),
    records_processed INTEGER,
    errors INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### 10. Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| API rate limits exceeded | Medium | High | Multiple API keys, provider rotation |
| Government site structure changes | Low | High | Automated testing, version control |
| Data enrichment costs exceed budget | Medium | Medium | Cost monitoring, tiered enrichment |
| Legal compliance issues | Low | Critical | Legal review, clear documentation |

---

## README - Quick Start Guide

### System Requirements

- Python 3.9+
- PostgreSQL 13+
- Redis 6+ (for queuing)
- RabbitMQ 3.8+ (for task distribution)
- 8GB RAM minimum
- 50GB storage for database

### Installation

```bash
# Clone the repository
git clone https://github.com/yourcompany/health-insurance-scraper.git
cd health-insurance-scraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# Initialize database
python scripts/init_db.py

# Run migrations
alembic upgrade head
```

### Configuration

Edit `.env` file with your credentials:

```env
# Government Data Sources
BLS_API_KEY=your_bls_api_key
SAM_GOV_API_KEY=your_sam_gov_key

# Enrichment Services
APOLLO_API_KEY=your_apollo_key
PROXYCURL_API_KEY=your_proxycurl_key
DROPCONTACT_API_KEY=your_dropcontact_key

# CRM Integration
PIPEDRIVE_API_KEY=your_pipedrive_key
PIPEDRIVE_DOMAIN=yourcompany.pipedrive.com
KIXIE_API_KEY=your_kixie_key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/lead_gen

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# RabbitMQ Configuration
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

### Quick Start

```bash
# Start all services
docker-compose up -d

# Run initial data collection
python -m scrapers.run_all --initial

# Start enrichment workers (in separate terminals)
python -m workers.enrichment_worker
python -m workers.scoring_worker
python -m workers.crm_sync_worker

# Monitor progress
python -m tools.monitor --dashboard
```

### Testing

```bash
# Run unit tests
pytest tests/unit

# Run integration tests
pytest tests/integration

# Run compliance checks
python -m tools.compliance_check
```

---

## Agent-Based Parallel Execution Strategy

### Overview

The system uses multiple specialized agents running in parallel to maximize throughput while respecting rate limits and maintaining data quality. Each agent has a specific responsibility and communicates through message queues.

### Agent Architecture

```mermaid
graph LR
    subgraph "Collection Agents"
        A1[BLS Agent 1]
        A2[BLS Agent 2]
        A3[SAM.gov Agent]
    end
    
    subgraph "Enrichment Agents"
        B1[Apollo Agent 1]
        B2[Apollo Agent 2]
        B3[Proxycurl Agent]
        B4[Email Verifier]
    end
    
    subgraph "Processing Agents"
        C1[Scoring Agent]
        C2[Dedup Agent]
        C3[CRM Sync Agent]
    end
    
    subgraph "Monitoring Agents"
        D1[Health Check]
        D2[Cost Monitor]
        D3[Quality Assurance]
    end
    
    A1 --> Q1[Collection Queue]
    A2 --> Q1
    A3 --> Q1
    
    Q1 --> B1
    Q1 --> B2
    Q1 --> B3
    
    B1 --> Q2[Enrichment Queue]
    B2 --> Q2
    B3 --> Q2
    B4 --> Q2
    
    Q2 --> C1
    Q2 --> C2
    
    C1 --> Q3[CRM Queue]
    C2 --> Q3
    
    Q3 --> C3
```

### Agent Specifications

#### 1. Collection Agents (3-5 parallel instances)

**Purpose:** Extract raw company data from government sources

**Configuration:**
```python
class CollectionAgent:
    def __init__(self, agent_id, source_type):
        self.agent_id = agent_id
        self.source_type = source_type
        self.rate_limit = self.get_rate_limit(source_type)
        self.batch_size = 100
        
    def run(self):
        while True:
            batch = self.get_next_batch()
            results = self.scrape_batch(batch)
            self.publish_to_queue(results)
            time.sleep(self.rate_limit)
```

**Parallelization Strategy:**
- BLS agents: 2 instances with 5-second delays
- SAM.gov agent: 1 instance with 3-second delay
- Geographic distribution: Each agent handles specific states

#### 2. Enrichment Agents (4-8 parallel instances)

**Purpose:** Add decision-maker contacts and verify information

**Configuration:**
```python
class EnrichmentAgent:
    def __init__(self, agent_id, provider):
        self.agent_id = agent_id
        self.provider = provider
        self.api_client = self.init_client(provider)
        self.cost_tracker = CostTracker(agent_id)
        
    def process_company(self, company):
        if self.should_enrich(company):
            contacts = self.api_client.find_contacts(company)
            self.cost_tracker.log_api_call(len(contacts))
            return self.validate_contacts(contacts)
```

**Parallelization Strategy:**
- Apollo agents: 3 instances with rotating API keys
- Proxycurl agent: 1 instance for LinkedIn data
- Email verifier: 2 instances processing in batches
- Load balancing: Round-robin distribution from queue

#### 3. Processing Agents (3-4 parallel instances)

**Purpose:** Score leads, remove duplicates, sync to CRM

**Configuration:**
```python
class ScoringAgent:
    def __init__(self):
        self.scoring_model = self.load_scoring_model()
        self.industry_weights = self.load_industry_config()
        
    def score_lead(self, company, contacts):
        base_score = self.calculate_base_score(company)
        industry_modifier = self.industry_weights.get(company.naics, 1.0)
        contact_quality = self.assess_contact_quality(contacts)
        
        return base_score * industry_modifier * contact_quality
```

**Parallelization Strategy:**
- Scoring agents: 2 instances for redundancy
- Deduplication: 1 instance with Redis cache
- CRM sync: 1 instance with retry logic

#### 4. Monitoring Agents (Always running)

**Purpose:** Ensure system health and compliance

**Configuration:**
```python
class MonitoringAgent:
    def __init__(self, check_type):
        self.check_type = check_type
        self.alert_manager = AlertManager()
        
    def run_checks(self):
        if self.check_type == 'health':
            self.check_api_availability()
            self.check_queue_depths()
            self.check_error_rates()
        elif self.check_type == 'cost':
            self.track_api_usage()
            self.project_monthly_costs()
        elif self.check_type == 'quality':
            self.validate_data_accuracy()
            self.check_compliance_rules()
```

### Queue Management

#### RabbitMQ Configuration

```yaml
# docker-compose.yml
services:
  rabbitmq:
    image: rabbitmq:3.8-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: secure_password
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
      
  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

#### Queue Definitions

```python
# queues.py
QUEUES = {
    'collection': {
        'name': 'companies.raw',
        'durable': True,
        'max_length': 10000,
        'ttl': 3600  # 1 hour
    },
    'enrichment': {
        'name': 'companies.enriched',
        'durable': True,
        'max_length': 5000,
        'ttl': 7200  # 2 hours
    },
    'crm_sync': {
        'name': 'companies.ready',
        'durable': True,
        'max_length': 1000,
        'ttl': 86400  # 24 hours
    }
}
```

### Parallel Execution Orchestration

```python
# orchestrator.py
class ParallelOrchestrator:
    def __init__(self):
        self.agents = []
        self.monitoring = []
        
    def start_all_agents(self):
        # Start collection agents
        for i in range(2):
            agent = CollectionAgent(f"bls_{i}", "BLS")
            self.agents.append(self.start_agent(agent))
            
        # Start enrichment agents
        for i in range(3):
            agent = EnrichmentAgent(f"apollo_{i}", "apollo")
            self.agents.append(self.start_agent(agent))
            
        # Start processing agents
        self.agents.append(self.start_agent(ScoringAgent()))
        self.agents.append(self.start_agent(CRMSyncAgent()))
        
        # Start monitors
        for check_type in ['health', 'cost', 'quality']:
            monitor = MonitoringAgent(check_type)
            self.monitoring.append(self.start_monitor(monitor))
    
    def start_agent(self, agent):
        process = multiprocessing.Process(target=agent.run)
        process.start()
        return process
```

---

## Implementation Lesson Plan

### Week 1: Foundation and Infrastructure

#### Day 1-2: Environment Setup
**Objective:** Establish development environment and project structure

**Why this matters:** A proper foundation prevents technical debt and ensures smooth collaboration.

**Tasks:**
1. Install Python 3.9+ and set up virtual environment
   ```bash
   # This isolates project dependencies
   python -m venv venv
   source venv/bin/activate
   ```

2. Create project structure:
   ```
   health-insurance-scraper/
   ├── scrapers/          # Data collection modules
   ├── enrichment/        # Contact discovery modules  
   ├── workers/           # Background processing agents
   ├── models/            # Database models
   ├── api/               # REST API endpoints
   ├── tests/             # Test suites
   └── config/            # Configuration files
   ```

3. Initialize Git repository with .gitignore:
   ```bash
   # Version control tracks changes and enables rollback
   git init
   echo "venv/\n*.pyc\n.env" > .gitignore
   git add .
   git commit -m "Initial project structure"
   ```

**Learning Objective:** Understand why proper project organization accelerates development and reduces errors.

#### Day 3-4: Database Design and Setup
**Objective:** Create robust data storage layer

**Why this matters:** Efficient data storage and retrieval is crucial for performance at scale.

**Tasks:**
1. Install PostgreSQL and create database:
   ```sql
   -- Relational database provides ACID compliance
   CREATE DATABASE lead_generation;
   CREATE USER scraper_app WITH PASSWORD 'secure_pass';
   GRANT ALL PRIVILEGES ON DATABASE lead_generation TO scraper_app;
   ```

2. Design schema with proper indexing:
   ```sql
   -- Indexes speed up queries by 100-1000x
   CREATE INDEX idx_companies_naics ON companies(naics_code);
   CREATE INDEX idx_companies_score ON companies(lead_score);
   CREATE INDEX idx_contacts_company ON contacts(company_id);
   ```

3. Set up SQLAlchemy ORM:
   ```python
   # ORM prevents SQL injection and provides abstraction
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker
   
   engine = create_engine('postgresql://user:pass@localhost/lead_gen')
   Session = sessionmaker(bind=engine)
   ```

**Learning Objective:** Understand how proper database design impacts system performance and maintainability.

#### Day 5: API Authentication and Rate Limiting
**Objective:** Implement secure API access with rate limiting

**Why this matters:** Protects against API bans and manages costs effectively.

**Tasks:**
1. Create API client base class:
   ```python
   class APIClient:
       def __init__(self, api_key, rate_limit=2):
           self.api_key = api_key
           self.rate_limit = rate_limit
           self.last_request = 0
           
       def make_request(self, endpoint, params):
           # Enforce rate limiting
           elapsed = time.time() - self.last_request
           if elapsed < self.rate_limit:
               time.sleep(self.rate_limit - elapsed)
           
           # Make request with retry logic
           response = self._request_with_retry(endpoint, params)
           self.last_request = time.time()
           return response
   ```

2. Implement credential management:
   ```python
   # Environment variables prevent credential exposure
   from dotenv import load_dotenv
   load_dotenv()
   
   API_KEYS = {
       'apollo': os.getenv('APOLLO_API_KEY'),
       'bls': os.getenv('BLS_API_KEY')
   }
   ```

**Learning Objective:** Learn why rate limiting and credential security are critical for production systems.

### Week 2: Core Scraping Implementation

#### Day 6-7: Government Data Scrapers
**Objective:** Build robust scrapers for public data sources

**Why this matters:** Government data provides free, legal, comprehensive business information.

**Tasks:**
1. Create BLS QCEW scraper:
   ```python
   class BLSQCEWScraper(scrapy.Spider):
       name = 'bls_qcew'
       
       def parse(self, response):
           # Parse JSON response
           data = response.json()
           
           # Filter for target employee ranges
           for establishment in data['Results']['series']:
               size_class = establishment['data'][0]['size_class']
               if size_class in ['5', '6', '7', '8']:  # 50-999 employees
                   yield {
                       'source': 'BLS',
                       'naics': establishment['naics_code'],
                       'size_class': size_class,
                       'area': establishment['area_code']
                   }
   ```

2. Implement compliance monitoring:
   ```python
   # Track all requests for audit trail
   class ComplianceMiddleware:
       def process_request(self, request, spider):
           log_entry = {
               'timestamp': datetime.now(),
               'url': request.url,
               'spider': spider.name,
               'headers': dict(request.headers)
           }
           self.compliance_log.append(log_entry)
   ```

**Learning Objective:** Understand how to extract value from government APIs while maintaining compliance.

#### Day 8-9: Enrichment Pipeline
**Objective:** Add decision-maker contact information

**Why this matters:** Direct contact with decision-makers increases conversion rates by 300%.

**Tasks:**
1. Implement Apollo.io integration:
   ```python
   class ApolloEnricher:
       def enrich_company(self, company_name, domain=None):
           # Search for company
           company_data = self.apollo.companies.search(
               name=company_name,
               domain=domain
           )
           
           # Find decision makers
           contacts = self.apollo.people.search(
               company_id=company_data['id'],
               titles=['HR Director', 'Benefits Manager', 'CFO']
           )
           
           return self.validate_contacts(contacts)
   ```

2. Create fallback enrichment strategy:
   ```python
   # Multiple providers ensure resilience
   class EnrichmentOrchestrator:
       def __init__(self):
           self.providers = [
               ApolloEnricher(),
               ProxycurlEnricher(),
               HunterEnricher()
           ]
           
       def enrich_with_fallback(self, company):
           for provider in self.providers:
               try:
                   contacts = provider.enrich_company(company)
                   if contacts:
                       return contacts
               except ProviderException:
                   continue
           return []
   ```

**Learning Objective:** Learn how redundancy and fallback strategies ensure system reliability.

#### Day 10: Lead Scoring Algorithm
**Objective:** Implement intelligent lead prioritization

**Why this matters:** Focusing on high-probability leads increases ROI by 400%.

**Tasks:**
1. Create scoring model:
   ```python
   class LeadScorer:
       def __init__(self):
           # Industry weights based on research
           self.industry_scores = {
               '541': 0.9,  # Professional services
               '518': 0.85, # Data processing
               '621': 0.8,  # Healthcare
               '523': 0.75  # Financial
           }
           
       def calculate_score(self, company):
           base_score = 50
           
           # Industry modifier
           naics_prefix = company['naics'][:3]
           industry_modifier = self.industry_scores.get(naics_prefix, 0.5)
           
           # Size modifier (sweet spot: 100-500 employees)
           size_score = self.calculate_size_score(company['employee_range'])
           
           # Contact quality modifier
           contact_score = len(company['contacts']) * 10
           
           return min(100, base_score * industry_modifier + size_score + contact_score)
   ```

2. Implement A/B testing framework:
   ```python
   # Test different scoring algorithms
   class ScoringExperiment:
       def __init__(self):
           self.algorithms = {
               'v1': self.score_v1,
               'v2': self.score_v2_with_geography
           }
           
       def run_experiment(self, company):
           algorithm = self.select_algorithm(company['id'])
           score = self.algorithms[algorithm](company)
           
           # Track for analysis
           self.track_score(company['id'], algorithm, score)
           return score
   ```

**Learning Objective:** Understand how data-driven scoring improves sales efficiency.

### Week 3: Integration and Automation

#### Day 11-12: CRM Integration
**Objective:** Seamlessly integrate with Pipedrive CRM

**Why this matters:** Automatic CRM updates save 2-3 hours per day per sales rep.

**Tasks:**
1. Implement Pipedrive API client:
   ```python
   class PipedriveClient:
       def __init__(self, api_key, domain):
           self.base_url = f"https://{domain}.pipedrive.com/api/v1"
           self.api_key = api_key
           
       def create_contact(self, contact_data):
           # Map our data to Pipedrive fields
           pipedrive_person = {
               'name': contact_data['full_name'],
               'email': contact_data['email'],
               'phone': contact_data['phone'],
               'org_id': self.get_or_create_org(contact_data['company']),
               # Custom fields
               'lead_score': contact_data['lead_score'],
               'data_source': 'Automated Scraper'
           }
           
           response = requests.post(
               f"{self.base_url}/persons",
               json=pipedrive_person,
               params={'api_token': self.api_key}
           )
           return response.json()
   ```

2. Create sync worker:
   ```python
   class CRMSyncWorker:
       def __init__(self):
           self.pipedrive = PipedriveClient()
           self.processed = set()
           
       def sync_batch(self, companies):
           for company in companies:
               if company['id'] not in self.processed:
                   # Create organization
                   org_id = self.pipedrive.create_organization(company)
                   
                   # Add contacts
                   for contact in company['contacts']:
                       contact['org_id'] = org_id
                       self.pipedrive.create_contact(contact)
                   
                   # Create deal for high-score leads
                   if company['lead_score'] > 80:
                       self.pipedrive.create_deal(company, org_id)
                   
                   self.processed.add(company['id'])
   ```

**Learning Objective:** Learn how API integrations multiply the value of collected data.

#### Day 13-14: Monitoring and Alerting
**Objective:** Build comprehensive monitoring system

**Why this matters:** Proactive monitoring prevents costly failures and data loss.

**Tasks:**
1. Create monitoring dashboard:
   ```python
   from flask import Flask, render_template
   import plotly.graph_objs as go
   
   app = Flask(__name__)
   
   @app.route('/dashboard')
   def dashboard():
       # Real-time metrics
       metrics = {
           'leads_today': get_leads_count(date.today()),
           'api_calls': get_api_usage(),
           'error_rate': calculate_error_rate(),
           'queue_depth': get_queue_sizes()
       }
       
       # Generate charts
       charts = {
           'leads_trend': create_leads_chart(),
           'api_costs': create_cost_chart(),
           'success_rate': create_success_chart()
       }
       
       return render_template('dashboard.html', 
                            metrics=metrics, 
                            charts=charts)
   ```

2. Implement alerting system:
   ```python
   class AlertManager:
       def __init__(self):
           self.thresholds = {
               'error_rate': 0.05,      # 5% error rate
               'api_cost_daily': 100,   # $100/day
               'queue_backup': 5000     # 5k items
           }
           
       def check_alerts(self):
           # Check each metric
           if self.get_error_rate() > self.thresholds['error_rate']:
               self.send_alert('High error rate detected', 'critical')
               
           if self.get_daily_cost() > self.thresholds['api_cost_daily']:
               self.send_alert('API costs exceeding budget', 'warning')
               
       def send_alert(self, message, severity):
           # Email notification
           send_email(ADMIN_EMAIL, f"[{severity}] {message}")
           
           # Slack notification
           slack_webhook.post(message, channel='#alerts')
   ```

**Learning Objective:** Understand how monitoring enables proactive system management.

#### Day 15: Performance Optimization
**Objective:** Optimize system for scale

**Why this matters:** Efficient code reduces infrastructure costs by 50-70%.

**Tasks:**
1. Implement caching layer:
   ```python
   class CachedEnricher:
       def __init__(self):
           self.redis = redis.Redis()
           self.ttl = 86400  # 24 hours
           
       def get_contacts(self, company_name):
           # Check cache first
           cache_key = f"contacts:{company_name}"
           cached = self.redis.get(cache_key)
           
           if cached:
               return json.loads(cached)
               
           # Fetch from API
           contacts = self.fetch_from_api(company_name)
           
           # Cache results
           self.redis.set(cache_key, json.dumps(contacts), ex=self.ttl)
           return contacts
   ```

2. Optimize database queries:
   ```python
   # Batch processing reduces database round trips
   class BatchProcessor:
       def process_companies(self, companies):
           # Bad: N+1 query problem
           # for company in companies:
           #     contacts = session.query(Contact).filter_by(company_id=company.id).all()
           
           # Good: Single query with join
           companies_with_contacts = session.query(Company)\
               .join(Contact)\
               .filter(Company.id.in_([c.id for c in companies]))\
               .options(joinedload(Company.contacts))\
               .all()
           
           return companies_with_contacts
   ```

**Learning Objective:** Learn how small optimizations compound into major performance gains.

### Week 4: Production Deployment

#### Day 16-17: Testing and Quality Assurance
**Objective:** Ensure system reliability through comprehensive testing

**Why this matters:** Bugs in production cost 10x more to fix than in development.

**Tasks:**
1. Write unit tests:
   ```python
   class TestLeadScorer(unittest.TestCase):
       def setUp(self):
           self.scorer = LeadScorer()
           
       def test_high_value_industry(self):
           company = {
               'naics': '541611',  # Management consulting
               'employee_range': '100-249',
               'contacts': [{'name': 'John Doe', 'title': 'HR Director'}]
           }
           score = self.scorer.calculate_score(company)
           self.assertGreater(score, 80)
           
       def test_low_value_industry(self):
           company = {
               'naics': '722511',  # Restaurant
               'employee_range': '50-99',
               'contacts': []
           }
           score = self.scorer.calculate_score(company)
           self.assertLess(score, 40)
   ```

2. Integration tests:
   ```python
   class TestEndToEnd(unittest.TestCase):
       def test_full_pipeline(self):
           # Create test company
           company = create_test_company()
           
           # Run through pipeline
           enriched = enricher.enrich_company(company)
           scored = scorer.calculate_score(enriched)
           
           # Verify CRM integration
           crm_sync.process_company(enriched)
           
           # Check results
           pipedrive_company = pipedrive.get_company(company['name'])
           self.assertIsNotNone(pipedrive_company)
           self.assertEqual(pipedrive_company['lead_score'], scored)
   ```

**Learning Objective:** Understand how testing prevents regressions and ensures reliability.

#### Day 18-19: Deployment and DevOps
**Objective:** Deploy system with proper DevOps practices

**Why this matters:** Good deployment practices enable rapid iteration and minimize downtime.

**Tasks:**
1. Create Docker containers:
   ```dockerfile
   # Dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   
   # Install dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application
   COPY . .
   
   # Run application
   CMD ["python", "-m", "workers.main"]
   ```

2. Set up docker-compose:
   ```yaml
   version: '3.8'
   services:
     scraper:
       build: .
       environment:
         - DATABASE_URL=postgresql://user:pass@db:5432/lead_gen
       depends_on:
         - db
         - redis
         - rabbitmq
       
     db:
       image: postgres:13
       environment:
         - POSTGRES_PASSWORD=secure_pass
       volumes:
         - postgres_data:/var/lib/postgresql/data
         
     redis:
       image: redis:6-alpine
       
     rabbitmq:
       image: rabbitmq:3.8-management
   ```

3. Implement CI/CD pipeline:
   ```yaml
   # .github/workflows/deploy.yml
   name: Deploy to Production
   
   on:
     push:
       branches: [main]
       
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         - name: Run tests
           run: |
             pip install -r requirements.txt
             pytest tests/
             
     deploy:
       needs: test
       runs-on: ubuntu-latest
       steps:
         - name: Deploy to server
           run: |
             ssh ${{ secrets.SERVER }} "cd /app && git pull && docker-compose up -d"
   ```

**Learning Objective:** Learn how containerization and CI/CD enable reliable deployments.

#### Day 20: Production Monitoring
**Objective:** Set up production monitoring and maintenance

**Why this matters:** Production visibility enables quick issue resolution.

**Tasks:**
1. Configure logging:
   ```python
   import logging
   from logging.handlers import RotatingFileHandler
   
   # Configure structured logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       handlers=[
           RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=5),
           logging.StreamHandler()
       ]
   )
   
   # Use structured logging
   logger = logging.getLogger(__name__)
   logger.info('Company enriched', extra={
       'company_id': company['id'],
       'contacts_found': len(contacts),
       'api_calls': api_calls_made
   })
   ```

2. Set up application monitoring:
   ```python
   # Health check endpoint
   @app.route('/health')
   def health_check():
       checks = {
           'database': check_database_connection(),
           'redis': check_redis_connection(),
           'apis': check_external_apis(),
           'queues': check_queue_health()
       }
       
       status = 'healthy' if all(checks.values()) else 'unhealthy'
       return jsonify({
           'status': status,
           'checks': checks,
           'timestamp': datetime.now().isoformat()
       })
   ```

**Learning Objective:** Understand how monitoring enables proactive system maintenance.

---

## Cursor IDE Prompts

### Initial Project Setup

```
Create a Python project structure for a web scraping system that collects business data from government sources, enriches it with contact information, and syncs to Pipedrive CRM. Include folders for scrapers, workers, models, tests, and configuration.
```

### Scraper Development

```
Create a Scrapy spider that extracts business data from the BLS QCEW API. The spider should:
1. Filter for businesses with 50-1200 employees
2. Extract NAICS codes, location, and size classifications
3. Implement rate limiting of 2 seconds between requests
4. Include error handling and retry logic
5. Log all requests for compliance tracking
```

### Enrichment Module

```
Build an enrichment module that takes company names and finds decision-maker contacts using Apollo.io API. Include:
1. Search for HR Directors, Benefits Managers, and CFOs
2. Fallback to Proxycurl if Apollo fails
3. Email verification through Dropcontact
4. Cost tracking for API calls
5. Caching to avoid duplicate lookups
```

### Lead Scoring

```
Implement a lead scoring algorithm that:
1. Scores companies 0-100 based on industry (NAICS code)
2. Gives bonus points for companies with 100-500 employees
3. Increases score based on number of decision-maker contacts found
4. Uses configurable industry weights
5. Includes A/B testing framework for algorithm variants
```

### CRM Integration

```
Create a Pipedrive CRM integration that:
1. Creates organizations for each company
2. Adds contacts with custom fields for lead score
3. Creates deals for leads scoring above 80
4. Handles rate limiting and retries
5. Tracks which records have been synced
```

### Monitoring Dashboard

```
Build a Flask web dashboard that displays:
1. Real-time lead generation metrics
2. API usage and costs breakdown
3. Error rates and system health
4. Queue depths and processing times
5. Use Plotly for interactive charts
```

### Docker Configuration

```
Create Docker configuration for the entire system including:
1. Python application container with all dependencies
2. PostgreSQL database with initial schema
3. Redis for caching and queues
4. RabbitMQ for task distribution
5. Docker-compose file linking all services
```

### Testing Suite

```
Write comprehensive tests including:
1. Unit tests for lead scoring algorithm
2. Integration tests for API clients
3. End-to-end test of full pipeline
4. Mocked external API responses
5. Performance benchmarks
```

Remember to explain your implementation choices and ask for clarification when needed. The goal is to build a production-ready system that can scale to process thousands of companies daily while maintaining compliance and data quality.