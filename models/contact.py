"""Contact model for storing decision-maker information."""

from datetime import datetime
from uuid import uuid4
from typing import Optional

from sqlalchemy import (
    Column, String, DateTime, Boolean, Text, 
    ForeignKey, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class Contact(Base):
    """Model for storing contact information for company decision-makers."""
    
    __tablename__ = "contacts"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign key to company
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Personal information
    full_name = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    middle_name = Column(String(100))
    
    # Professional information
    title = Column(String(255), index=True)
    department = Column(String(100))
    seniority_level = Column(String(50))  # C-Level, VP, Director, Manager
    is_decision_maker = Column(Boolean, default=False)
    
    # Contact information
    email = Column(String(255), index=True)
    email_verified = Column(Boolean, default=False)
    email_verification_date = Column(DateTime)
    
    phone = Column(String(50))
    phone_type = Column(String(20))  # mobile, work, etc.
    phone_verified = Column(Boolean, default=False)
    
    # Social profiles
    linkedin_url = Column(Text)
    linkedin_id = Column(String(100))
    twitter_handle = Column(String(100))
    
    # Data source
    source = Column(String(50), nullable=False)  # apollo, proxycurl, manual
    source_id = Column(String(100))
    confidence_score = Column(String(20))  # high, medium, low
    
    # Processing status
    crm_sync_status = Column(String(20), default="pending")
    pipedrive_person_id = Column(String(50))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_verified_at = Column(DateTime)
    
    # Additional data
    extra_data = Column(JSON, default=dict)
    
    # Relationships
    company = relationship("Company", back_populates="contacts")
    
    # Table constraints
    __table_args__ = (
        Index("idx_contact_company", "company_id"),
        Index("idx_contact_email", "email"),
        Index("idx_contact_title", "title"),
        Index("idx_contact_decision_maker", "is_decision_maker", "company_id"),
    )
    
    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, name='{self.full_name}', title='{self.title}')>"
    
    @property
    def is_executive(self) -> bool:
        """Check if contact is an executive level decision maker."""
        executive_keywords = [
            "CEO", "CFO", "COO", "CTO", "President", "Owner",
            "Vice President", "VP", "Director", "Head of"
        ]
        if not self.title:
            return False
        return any(keyword.lower() in self.title.lower() for keyword in executive_keywords)
    
    @property
    def is_hr_related(self) -> bool:
        """Check if contact is in HR/Benefits department."""
        hr_keywords = [
            "HR", "Human Resources", "Benefits", "Compensation",
            "People", "Talent", "Employee"
        ]
        title_check = self.title and any(keyword.lower() in self.title.lower() for keyword in hr_keywords)
        dept_check = self.department and any(keyword.lower() in self.department.lower() for keyword in hr_keywords)
        return title_check or dept_check
    
    def to_dict(self) -> dict:
        """Convert contact to dictionary representation."""
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "title": self.title,
            "department": self.department,
            "email": self.email,
            "email_verified": self.email_verified,
            "phone": self.phone,
            "linkedin_url": self.linkedin_url,
            "is_decision_maker": self.is_decision_maker,
            "is_executive": self.is_executive,
            "is_hr_related": self.is_hr_related,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        } 