"""API usage model for tracking external API calls and costs."""

from datetime import datetime
from uuid import uuid4
from decimal import Decimal

from sqlalchemy import Column, String, Integer, DateTime, Numeric, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class ApiUsage(Base):
    """Model for tracking API usage and costs across different providers."""
    
    __tablename__ = "api_usage"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # API provider information
    provider = Column(String(50), nullable=False, index=True)  # apollo, proxycurl, dropcontact, etc.
    endpoint = Column(String(255))  # Specific API endpoint called
    api_key_id = Column(String(50))  # To track which API key was used
    
    # Request details
    request_type = Column(String(20))  # search, enrich, verify, etc.
    request_count = Column(Integer, default=1)  # For batch requests
    response_status = Column(Integer)  # HTTP status code
    success = Column(Boolean, default=True)
    
    # Cost tracking
    credits_used = Column(Integer, default=0)
    cost_per_request = Column(Numeric(10, 4), default=0)  # Cost in USD
    total_cost = Column(Numeric(10, 4), default=0)  # Total cost for this usage
    
    # Response metrics
    response_time_ms = Column(Integer)  # Response time in milliseconds
    records_returned = Column(Integer, default=0)
    
    # Monthly tracking
    month = Column(String(7), index=True)  # Format: YYYY-MM
    daily_count = Column(Integer, default=0)  # Count for the specific day
    
    # Related entities
    company_id = Column(UUID(as_uuid=True))  # If API call was for a specific company
    batch_id = Column(String(50))  # For grouping related API calls
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    worker_id = Column(String(50))  # ID of the worker that made the call
    
    # Table constraints
    __table_args__ = (
        Index("idx_api_usage_provider_month", "provider", "month"),
        Index("idx_api_usage_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ApiUsage(id={self.id}, provider='{self.provider}', cost={self.total_cost})>"
    
    @classmethod
    def calculate_cost(cls, provider: str, request_type: str, count: int = 1) -> Decimal:
        """Calculate the cost for a specific API request."""
        # Cost mapping per provider (example rates)
        cost_map = {
            "apollo": {
                "search": Decimal("0.01"),
                "enrich": Decimal("0.05"),
                "verify": Decimal("0.02"),
            },
            "proxycurl": {
                "profile": Decimal("0.10"),
                "company": Decimal("0.15"),
            },
            "dropcontact": {
                "verify": Decimal("0.01"),
                "enrich": Decimal("0.03"),
            },
            "hunter": {
                "verify": Decimal("0.01"),
                "search": Decimal("0.02"),
            },
        }
        
        provider_costs = cost_map.get(provider.lower(), {})
        cost_per_request = provider_costs.get(request_type.lower(), Decimal("0.01"))
        return cost_per_request * count
    
    def to_dict(self) -> dict:
        """Convert API usage to dictionary representation."""
        return {
            "id": str(self.id),
            "provider": self.provider,
            "endpoint": self.endpoint,
            "request_type": self.request_type,
            "request_count": self.request_count,
            "success": self.success,
            "credits_used": self.credits_used,
            "total_cost": float(self.total_cost) if self.total_cost else 0,
            "response_time_ms": self.response_time_ms,
            "records_returned": self.records_returned,
            "month": self.month,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        } 