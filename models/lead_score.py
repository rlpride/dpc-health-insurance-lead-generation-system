"""Lead score model for tracking scoring history and calculations."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class LeadScore(Base):
    """Model for tracking lead scoring history and detailed calculations."""
    
    __tablename__ = "lead_scores"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign key to company
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Overall score
    total_score = Column(Integer, nullable=False)  # 0-100
    score_grade = Column(String(2))  # A+, A, B+, B, C, etc.
    
    # Component scores
    industry_score = Column(Integer)  # Based on NAICS code risk profile
    size_score = Column(Integer)  # Based on employee count fit
    location_score = Column(Integer)  # Based on geographic factors
    data_quality_score = Column(Integer)  # Based on data completeness
    engagement_score = Column(Integer)  # Based on previous interactions
    
    # Scoring factors
    scoring_factors = Column(JSON)  # Detailed breakdown of scoring factors
    
    # Industry-specific metrics
    industry_risk_level = Column(String(20))  # high, medium, low
    industry_multiplier = Column(Float, default=1.0)
    
    # Size-specific metrics
    employee_count_used = Column(Integer)  # Actual count used in calculation
    size_category = Column(String(20))  # small, medium, large
    
    # Reasons and recommendations
    score_reasons = Column(JSON)  # List of reasons for the score
    recommendations = Column(Text)  # AI-generated recommendations
    
    # Metadata
    scoring_version = Column(String(10), default="1.0")  # Version of scoring algorithm
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(50))  # System or user that triggered scoring
    
    # Relationships
    company = relationship("Company", back_populates="lead_scores")
    
    def __repr__(self) -> str:
        return f"<LeadScore(id={self.id}, company_id={self.company_id}, score={self.total_score})>"
    
    @staticmethod
    def calculate_grade(score: int) -> str:
        """Convert numeric score to letter grade."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "A-"
        elif score >= 80:
            return "B+"
        elif score >= 75:
            return "B"
        elif score >= 70:
            return "B-"
        elif score >= 65:
            return "C+"
        elif score >= 60:
            return "C"
        elif score >= 55:
            return "C-"
        else:
            return "D"
    
    @property
    def is_high_quality(self) -> bool:
        """Check if this is a high-quality lead."""
        return self.total_score >= 80
    
    @property
    def is_medium_quality(self) -> bool:
        """Check if this is a medium-quality lead."""
        return 60 <= self.total_score < 80
    
    def to_dict(self) -> dict:
        """Convert lead score to dictionary representation."""
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "total_score": self.total_score,
            "score_grade": self.score_grade,
            "industry_score": self.industry_score,
            "size_score": self.size_score,
            "location_score": self.location_score,
            "data_quality_score": self.data_quality_score,
            "engagement_score": self.engagement_score,
            "industry_risk_level": self.industry_risk_level,
            "size_category": self.size_category,
            "scoring_factors": self.scoring_factors,
            "score_reasons": self.score_reasons,
            "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        } 