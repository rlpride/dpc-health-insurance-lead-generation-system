-- PostgreSQL initialization script for Lead Generation System
-- This script will be executed when the PostgreSQL container starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create database schema
\c lead_generation;

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255),
    dba_name VARCHAR(255),
    
    -- Industry classification
    naics_code VARCHAR(6),
    naics_description TEXT,
    sic_code VARCHAR(4),
    industry_category VARCHAR(100),
    
    -- Company size
    employee_range VARCHAR(50),
    employee_count_min INTEGER,
    employee_count_max INTEGER,
    employee_count_exact INTEGER,
    annual_revenue FLOAT,
    
    -- Location
    street_address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(2),
    zip_code VARCHAR(10),
    county VARCHAR(100),
    country VARCHAR(2) DEFAULT 'US',
    latitude FLOAT,
    longitude FLOAT,
    
    -- Contact information
    phone VARCHAR(50),
    website VARCHAR(255),
    email_domain VARCHAR(100),
    
    -- Government identifiers
    ein VARCHAR(20),
    duns_number VARCHAR(20),
    cage_code VARCHAR(10),
    
    -- Data source
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(100),
    source_url TEXT,
    
    -- Lead scoring
    lead_score INTEGER DEFAULT 0,
    industry_risk_score INTEGER,
    size_fit_score INTEGER,
    location_score INTEGER,
    
    -- Processing status
    enrichment_status VARCHAR(20) DEFAULT 'pending',
    crm_sync_status VARCHAR(20) DEFAULT 'pending',
    pipedrive_id VARCHAR(50),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_enriched_at TIMESTAMP,
    last_verified_at TIMESTAMP,
    
    -- Additional data
    extra_data JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT check_employee_range CHECK (employee_count_min IS NULL OR employee_count_max IS NULL OR employee_count_min <= employee_count_max),
    CONSTRAINT check_lead_score_range CHECK (lead_score >= 0 AND lead_score <= 100)
);

-- Contacts table
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Personal information
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(200),
    title VARCHAR(150),
    department VARCHAR(100),
    seniority_level VARCHAR(50),
    
    -- Contact information
    email VARCHAR(255),
    phone VARCHAR(50),
    mobile_phone VARCHAR(50),
    linkedin_url VARCHAR(500),
    
    -- Verification status
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    
    -- Data source
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(100),
    confidence_score INTEGER DEFAULT 0,
    
    -- Processing status
    enrichment_status VARCHAR(20) DEFAULT 'pending',
    crm_sync_status VARCHAR(20) DEFAULT 'pending',
    pipedrive_person_id VARCHAR(50),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_enriched_at TIMESTAMP,
    
    -- Additional data
    extra_data JSONB DEFAULT '{}'
);

-- Lead scores table
CREATE TABLE IF NOT EXISTS lead_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Scoring components
    overall_score INTEGER NOT NULL,
    industry_score INTEGER DEFAULT 0,
    size_score INTEGER DEFAULT 0,
    location_score INTEGER DEFAULT 0,
    technology_score INTEGER DEFAULT 0,
    growth_score INTEGER DEFAULT 0,
    
    -- Scoring details
    scoring_model_version VARCHAR(20) DEFAULT '1.0',
    scoring_factors JSONB DEFAULT '{}',
    
    -- Metadata
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    
    CONSTRAINT check_overall_score_range CHECK (overall_score >= 0 AND overall_score <= 100)
);

-- API usage tracking table
CREATE TABLE IF NOT EXISTS api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- API details
    api_name VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255),
    method VARCHAR(10),
    
    -- Usage tracking
    request_count INTEGER DEFAULT 1,
    cost_per_request DECIMAL(10,4),
    total_cost DECIMAL(10,2),
    
    -- Rate limiting
    requests_per_hour INTEGER DEFAULT 0,
    daily_limit INTEGER,
    monthly_limit INTEGER,
    
    -- Status
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_error_message TEXT,
    
    -- Metadata
    date DATE DEFAULT CURRENT_DATE,
    hour INTEGER DEFAULT EXTRACT(hour FROM CURRENT_TIMESTAMP),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scraping logs table
CREATE TABLE IF NOT EXISTS scraping_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Scraping session details
    scraper_name VARCHAR(100) NOT NULL,
    session_id VARCHAR(100),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',
    
    -- Statistics
    records_processed INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    
    -- Error tracking
    error_message TEXT,
    error_details JSONB DEFAULT '{}',
    
    -- Configuration
    scraper_config JSONB DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name);
CREATE INDEX IF NOT EXISTS idx_companies_naics_code ON companies(naics_code);
CREATE INDEX IF NOT EXISTS idx_companies_city ON companies(city);
CREATE INDEX IF NOT EXISTS idx_companies_state ON companies(state);
CREATE INDEX IF NOT EXISTS idx_companies_lead_score ON companies(lead_score);
CREATE INDEX IF NOT EXISTS idx_companies_score_state ON companies(lead_score, state);
CREATE INDEX IF NOT EXISTS idx_companies_enrichment ON companies(enrichment_status, created_at);
CREATE INDEX IF NOT EXISTS idx_companies_source ON companies(source);

CREATE INDEX IF NOT EXISTS idx_contacts_company_id ON contacts(company_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
CREATE INDEX IF NOT EXISTS idx_contacts_source ON contacts(source);

CREATE INDEX IF NOT EXISTS idx_lead_scores_company_id ON lead_scores(company_id);
CREATE INDEX IF NOT EXISTS idx_lead_scores_overall ON lead_scores(overall_score);

CREATE INDEX IF NOT EXISTS idx_api_usage_name_date ON api_usage(api_name, date);
CREATE INDEX IF NOT EXISTS idx_scraping_logs_scraper ON scraping_logs(scraper_name, start_time);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_usage_updated_at BEFORE UPDATE ON api_usage
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert some initial configuration data
INSERT INTO api_usage (api_name, daily_limit, monthly_limit, requests_per_hour) 
VALUES 
    ('BLS', 500, 10000, 100),
    ('SAM_GOV', 1000, 20000, 200),
    ('APOLLO', 1000, 10000, 100),
    ('PROXYCURL', 100, 5000, 50),
    ('DROPCONTACT', 500, 20000, 200)
ON CONFLICT DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;