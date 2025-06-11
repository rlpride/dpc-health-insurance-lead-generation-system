"""Company model for storing business information."""

from datetime import datetime
from uuid import uuid4
from typing import List, Optional

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, 
    Text, JSON, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class Company(Base):
    """Model for storing company information collected from various sources."""
    
    __tablename__ = "companies"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Basic company information
    name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255))
    dba_name = Column(String(255))
    
    # Industry classification
    naics_code = Column(String(6), index=True)
    naics_description = Column(Text)
    sic_code = Column(String(4))
    industry_category = Column(String(100))
    
    # Company size
    employee_range = Column(String(50))  # e.g., "50-200"
    employee_count_min = Column(Integer)
    employee_count_max = Column(Integer)
    employee_count_exact = Column(Integer)  # If known exactly
    annual_revenue = Column(Float)
    
    # Location information
    street_address = Column(String(255))
    city = Column(String(100), index=True)
    state = Column(String(2), index=True)
    zip_code = Column(String(10))
    county = Column(String(100))
    country = Column(String(2), default="US")
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Contact information
    phone = Column(String(50))
    website = Column(String(255))
    email_domain = Column(String(100))
    
    # Government identifiers
    ein = Column(String(20))  # Employer Identification Number
    duns_number = Column(String(20))  # D-U-N-S Number
    cage_code = Column(String(10))  # SAM.gov CAGE code
    
    # Data source information
    source = Column(String(50), nullable=False)  # 'BLS', 'SAM_GOV', etc.
    source_id = Column(String(100))  # ID in the source system
    source_url = Column(Text)
    
    # Lead scoring
    lead_score = Column(Integer, default=0, index=True)
    industry_risk_score = Column(Integer)
    size_fit_score = Column(Integer)
    location_score = Column(Integer)
    
    # Processing status
    enrichment_status = Column(String(20), default="pending")  # pending, enriched, failed
    crm_sync_status = Column(String(20), default="pending")  # pending, synced, failed
    pipedrive_id = Column(String(50))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_enriched_at = Column(DateTime)
    last_verified_at = Column(DateTime)
    
    # Additional data stored as JSON
    extra_data = Column(JSON, default=dict)
    
    # Relationships
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    lead_scores = relationship("LeadScore", back_populates="company", cascade="all, delete-orphan")
    
    # Table constraints
    __table_args__ = (
        Index("idx_company_score_state", "lead_score", "state"),
        Index("idx_company_enrichment", "enrichment_status", "created_at"),
        CheckConstraint("employee_count_min <= employee_count_max", name="check_employee_range"),
        CheckConstraint("lead_score >= 0 AND lead_score <= 100", name="check_lead_score_range"),
    )
    
    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name='{self.name}', state='{self.state}', score={self.lead_score})>"
    
    @property
    def is_qualified(self) -> bool:
        """Check if company meets basic qualification criteria."""
        if not self.employee_count_min:
            return False
        return 50 <= self.employee_count_min <= 1200
    
    @property
    def needs_enrichment(self) -> bool:
        """Check if company needs enrichment."""
        return self.enrichment_status == "pending"
    
    def to_dict(self) -> dict:
        """Convert company to dictionary representation."""
        return {
            "id": str(self.id),
            "name": self.name,
            "legal_name": self.legal_name,
            "naics_code": self.naics_code,
            "employee_range": self.employee_range,
            "city": self.city,
            "state": self.state,
            "lead_score": self.lead_score,
            "website": self.website,
            "phone": self.phone,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        } 