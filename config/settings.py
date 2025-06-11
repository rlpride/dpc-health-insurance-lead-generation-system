"""Application settings management using Pydantic."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn, AmqpDsn


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application Settings
    env: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    secret_key: str = Field(description="Secret key for encryption")
    
    # Government Data Sources
    bls_api_key: str = Field(description="Bureau of Labor Statistics API key")
    sam_gov_api_key: str = Field(description="SAM.gov API key")
    
    # Enrichment Services
    apollo_api_key: str = Field(description="Apollo.io API key")
    proxycurl_api_key: Optional[str] = Field(default=None, description="Proxycurl API key")
    dropcontact_api_key: Optional[str] = Field(default=None, description="Dropcontact API key")
    hunter_api_key: Optional[str] = Field(default=None, description="Hunter.io API key")
    
    # CRM Integration
    pipedrive_api_key: str = Field(description="Pipedrive API key")
    pipedrive_domain: str = Field(description="Pipedrive domain")
    kixie_api_key: Optional[str] = Field(default=None, description="Kixie API key")
    
    # Database Configuration
    database_url: PostgresDsn = Field(description="PostgreSQL connection URL")
    database_pool_size: int = Field(default=20, description="Database pool size")
    database_max_overflow: int = Field(default=40, description="Database max overflow")
    
    # Redis Configuration
    redis_url: RedisDsn = Field(description="Redis connection URL")
    redis_max_connections: int = Field(default=50, description="Redis max connections")
    
    # RabbitMQ Configuration
    rabbitmq_url: AmqpDsn = Field(description="RabbitMQ connection URL")
    rabbitmq_heartbeat: int = Field(default=600, description="RabbitMQ heartbeat interval")
    rabbitmq_connection_attempts: int = Field(default=3, description="Connection retry attempts")
    
    # Rate Limiting
    bls_rate_limit_seconds: int = Field(default=5, ge=1, description="BLS API rate limit")
    sam_gov_rate_limit_seconds: int = Field(default=3, ge=1, description="SAM.gov rate limit")
    apollo_rate_limit_seconds: int = Field(default=2, ge=1, description="Apollo rate limit")
    enrichment_batch_size: int = Field(default=50, ge=1, le=100, description="Enrichment batch size")
    
    # Workers Configuration
    max_collection_workers: int = Field(default=3, ge=1, le=10, description="Max collection workers")
    max_enrichment_workers: int = Field(default=5, ge=1, le=20, description="Max enrichment workers")
    max_processing_workers: int = Field(default=3, ge=1, le=10, description="Max processing workers")
    
    # Lead Scoring Thresholds
    min_employee_count: int = Field(default=50, ge=1, description="Minimum employee count")
    max_employee_count: int = Field(default=1200, ge=100, description="Maximum employee count")
    high_score_threshold: int = Field(default=80, ge=0, le=100, description="High score threshold")
    medium_score_threshold: int = Field(default=60, ge=0, le=100, description="Medium score threshold")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    prometheus_metrics_port: int = Field(default=9090, description="Prometheus metrics port")
    health_check_interval: int = Field(default=60, ge=10, description="Health check interval")
    
    # Email Notifications
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_username: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    notification_email: Optional[str] = Field(default=None, description="Admin notification email")
    
    # Data Retention
    data_retention_days: int = Field(default=90, ge=30, description="Data retention period")
    log_retention_days: int = Field(default=30, ge=7, description="Log retention period")
    
    # API Cost Limits
    apollo_monthly_limit: int = Field(default=10000, ge=0, description="Apollo monthly API limit")
    proxycurl_monthly_limit: int = Field(default=5000, ge=0, description="Proxycurl monthly limit")
    dropcontact_monthly_limit: int = Field(default=20000, ge=0, description="Dropcontact monthly limit")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.env.lower() == "development"
    
    def get_rate_limit(self, source: str) -> int:
        """Get rate limit for a specific data source."""
        rate_limits = {
            "bls": self.bls_rate_limit_seconds,
            "sam_gov": self.sam_gov_rate_limit_seconds,
            "apollo": self.apollo_rate_limit_seconds,
        }
        return rate_limits.get(source.lower(), 5)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 