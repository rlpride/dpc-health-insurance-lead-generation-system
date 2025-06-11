"""Lead scoring algorithm implementation with A/B testing support."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from config.lead_scoring import LeadScoringConfig, IndustryWeight
from models.company import Company
from models.contact import Contact
from models.lead_score import LeadScore


logger = logging.getLogger(__name__)


class LeadScoringService:
    """Service for calculating lead scores with A/B testing support."""
    
    def __init__(self, config: LeadScoringConfig = None):
        """Initialize the lead scoring service."""
        self.config = config or LeadScoringConfig()
        self.logger = logger
    
    def calculate_score(
        self,
        company: Company,
        contacts: List[Contact] = None,
        algorithm_variant: str = None
    ) -> LeadScore:
        """
        Calculate comprehensive lead score for a company.
        
        Args:
            company: Company instance to score
            contacts: List of contacts for the company (optional, will query if not provided)
            algorithm_variant: Specific algorithm variant to use (for A/B testing)
        
        Returns:
            LeadScore instance with detailed scoring breakdown
        """
        try:
            # Determine algorithm variant
            variant = algorithm_variant or self._get_algorithm_variant(company.id)
            variant_config = self._get_variant_config(variant)
            
            # Get contacts if not provided
            if contacts is None:
                contacts = company.contacts or []
            
            # Calculate component scores
            industry_score = self._calculate_industry_score(company)
            size_score = self._calculate_size_score(company)
            contact_score = self._calculate_contact_score(contacts)
            data_quality_score = self._calculate_data_quality_score(company)
            
            # Apply variant-specific weights
            weighted_scores = {
                "industry": industry_score * variant_config["industry_weight"],
                "size": size_score * variant_config["size_weight"],
                "contact": contact_score * variant_config["contact_weight"],
                "data_quality": data_quality_score * variant_config["data_quality_weight"],
            }
            
            # Calculate total score
            total_score = min(100, sum(weighted_scores.values()))
            
            # Generate scoring factors and reasons
            scoring_factors = self._generate_scoring_factors(
                company, contacts, industry_score, size_score, contact_score, data_quality_score
            )
            score_reasons = self._generate_score_reasons(scoring_factors, total_score)
            
            # Create LeadScore instance
            lead_score = LeadScore(
                company_id=company.id,
                total_score=int(total_score),
                score_grade=LeadScore.calculate_grade(int(total_score)),
                industry_score=int(industry_score),
                size_score=int(size_score),
                location_score=0,  # Not implemented in this version
                data_quality_score=int(data_quality_score),
                engagement_score=int(contact_score),
                scoring_factors=scoring_factors,
                industry_risk_level=self.config.get_industry_weight(company.naics_code).risk_level,
                industry_multiplier=self.config.get_industry_weight(company.naics_code).weight,
                employee_count_used=self._get_employee_count(company),
                size_category=self.config.get_employee_size_config(self._get_employee_count(company))["category"],
                score_reasons=score_reasons,
                recommendations=self._generate_recommendations(company, total_score),
                scoring_version=variant_config["version"],
                created_by=f"algorithm_{variant}",
            )
            
            self.logger.info(
                f"Calculated lead score for {company.name}: {total_score} "
                f"(Industry: {industry_score}, Size: {size_score}, "
                f"Contact: {contact_score}, Quality: {data_quality_score})"
            )
            
            return lead_score
            
        except Exception as e:
            self.logger.error(f"Error calculating lead score for {company.name}: {str(e)}")
            raise
    
    def _calculate_industry_score(self, company: Company) -> float:
        """Calculate industry-based score using NAICS code."""
        industry_config = self.config.get_industry_weight(company.naics_code)
        base_score = industry_config.base_score
        weight = industry_config.weight
        
        # Apply industry weight
        score = base_score * weight
        
        # Cap at 100
        return min(100.0, score)
    
    def _calculate_size_score(self, company: Company) -> float:
        """Calculate size-based score with bonus for optimal range."""
        employee_count = self._get_employee_count(company)
        
        if employee_count == 0:
            return 20.0  # Default low score for unknown size
        
        size_config = self.config.get_employee_size_config(employee_count)
        base_score = size_config["score"]
        bonus = size_config["bonus"]
        
        # Additional bonus for being in the optimal range (100-500 employees)
        if self.config.employee_size.optimal_min <= employee_count <= self.config.employee_size.optimal_max:
            bonus += self.config.employee_size.bonus_points
        
        return min(100.0, base_score + bonus)
    
    def _calculate_contact_score(self, contacts: List[Contact]) -> float:
        """Calculate score based on decision-maker contacts found."""
        if not contacts:
            return 0.0
        
        config = self.config.contact_scoring
        score = 0.0
        
        decision_makers = [c for c in contacts if c.is_decision_maker]
        executives = [c for c in contacts if c.is_executive]
        hr_contacts = [c for c in contacts if c.is_hr_related]
        verified_emails = [c for c in contacts if c.email_verified]
        
        # Base points for decision makers
        score += len(decision_makers) * config.decision_maker_base_points
        
        # Executive bonus
        score += len(executives) * config.executive_bonus_points
        
        # HR/Benefits contact bonus
        score += len(hr_contacts) * config.hr_benefits_bonus_points
        
        # Verified email bonus
        score += len(verified_emails) * config.verified_email_bonus
        
        # Multiple contacts bonus
        if len(contacts) >= 3:
            score += config.multiple_contacts_bonus
        
        # Cap at maximum
        return min(float(config.max_contact_score), score)
    
    def _calculate_data_quality_score(self, company: Company) -> float:
        """Calculate score based on data completeness and quality."""
        score = 0.0
        weights = self.config.data_quality_weights
        
        # Check various data quality factors
        if company.website:
            score += weights["has_website"]
        
        if company.phone:
            score += weights["has_phone"]
        
        if company.email_domain:
            score += weights["has_email_domain"]
        
        if company.street_address and company.city and company.state:
            score += weights["has_address"]
        
        if company.ein:
            score += weights["has_ein"]
        
        # Recent data bonus (updated within last 30 days)
        if company.updated_at and company.updated_at > datetime.utcnow() - timedelta(days=30):
            score += weights["recent_data"]
        
        return min(20.0, float(score))  # Cap data quality at 20 points
    
    def _get_employee_count(self, company: Company) -> int:
        """Get the best available employee count for a company."""
        if company.employee_count_exact:
            return company.employee_count_exact
        
        if company.employee_count_min and company.employee_count_max:
            # Use midpoint of range
            return (company.employee_count_min + company.employee_count_max) // 2
        
        if company.employee_count_min:
            return company.employee_count_min
        
        # Try to parse from employee_range string
        if company.employee_range:
            try:
                if "-" in company.employee_range:
                    min_val, max_val = company.employee_range.split("-")
                    return (int(min_val) + int(max_val.rstrip("+"))) // 2
                elif company.employee_range.endswith("+"):
                    return int(company.employee_range.rstrip("+"))
                else:
                    return int(company.employee_range)
            except (ValueError, AttributeError):
                pass
        
        return 0
    
    def _get_algorithm_variant(self, company_id: UUID) -> str:
        """Determine algorithm variant for A/B testing."""
        if not self.config.ab_testing.enabled:
            return "control"
        
        # Use company ID hash for consistent variant assignment
        hash_input = str(company_id).encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        
        # Determine variant based on weights
        total_weight = sum(self.config.ab_testing.variant_weights.values())
        normalized_hash = (hash_value % 1000) / 1000.0  # 0.0 to 1.0
        
        cumulative_weight = 0.0
        for variant, weight in self.config.ab_testing.variant_weights.items():
            cumulative_weight += weight / total_weight
            if normalized_hash <= cumulative_weight:
                return variant
        
        return "control"  # Fallback
    
    def _get_variant_config(self, variant: str) -> Dict[str, Any]:
        """Get configuration for a specific algorithm variant."""
        variants = self.config.ab_testing.algorithm_variants
        return variants.get(variant, variants["control"])
    
    def _generate_scoring_factors(
        self, 
        company: Company, 
        contacts: List[Contact], 
        industry_score: float,
        size_score: float,
        contact_score: float,
        data_quality_score: float
    ) -> Dict[str, Any]:
        """Generate detailed scoring factors breakdown."""
        return {
            "industry": {
                "naics_code": company.naics_code,
                "naics_description": company.naics_description,
                "base_score": self.config.get_industry_weight(company.naics_code).base_score,
                "weight": self.config.get_industry_weight(company.naics_code).weight,
                "final_score": industry_score,
                "risk_level": self.config.get_industry_weight(company.naics_code).risk_level,
            },
            "size": {
                "employee_count": self._get_employee_count(company),
                "employee_range": company.employee_range,
                "size_category": self.config.get_employee_size_config(self._get_employee_count(company))["category"],
                "base_score": self.config.get_employee_size_config(self._get_employee_count(company))["score"],
                "bonus_points": self.config.get_employee_size_config(self._get_employee_count(company))["bonus"],
                "final_score": size_score,
                "in_optimal_range": (
                    self.config.employee_size.optimal_min <= 
                    self._get_employee_count(company) <= 
                    self.config.employee_size.optimal_max
                ),
            },
            "contacts": {
                "total_contacts": len(contacts),
                "decision_makers": len([c for c in contacts if c.is_decision_maker]),
                "executives": len([c for c in contacts if c.is_executive]),
                "hr_contacts": len([c for c in contacts if c.is_hr_related]),
                "verified_emails": len([c for c in contacts if c.email_verified]),
                "final_score": contact_score,
            },
            "data_quality": {
                "has_website": bool(company.website),
                "has_phone": bool(company.phone),
                "has_email_domain": bool(company.email_domain),
                "has_complete_address": bool(company.street_address and company.city and company.state),
                "has_ein": bool(company.ein),
                "recent_update": bool(
                    company.updated_at and 
                    company.updated_at > datetime.utcnow() - timedelta(days=30)
                ),
                "final_score": data_quality_score,
            }
        }
    
    def _generate_score_reasons(self, scoring_factors: Dict[str, Any], total_score: float) -> List[str]:
        """Generate human-readable reasons for the score."""
        reasons = []
        
        # Industry reasons
        industry = scoring_factors["industry"]
        if industry["risk_level"] == "low":
            reasons.append(f"Low-risk industry: {industry['naics_description']}")
        elif industry["risk_level"] == "high":
            reasons.append(f"High-risk industry: {industry['naics_description']}")
        
        # Size reasons
        size = scoring_factors["size"]
        if size["in_optimal_range"]:
            reasons.append(f"Optimal company size: {size['employee_count']} employees")
        elif size["employee_count"] > 1000:
            reasons.append("Large company size may indicate complex decision-making")
        elif size["employee_count"] < 50:
            reasons.append("Small company size may limit insurance budget")
        
        # Contact reasons
        contacts = scoring_factors["contacts"]
        if contacts["decision_makers"] > 0:
            reasons.append(f"Found {contacts['decision_makers']} decision-maker contact(s)")
        if contacts["executives"] > 0:
            reasons.append(f"Found {contacts['executives']} executive contact(s)")
        if contacts["hr_contacts"] > 0:
            reasons.append(f"Found {contacts['hr_contacts']} HR/benefits contact(s)")
        if contacts["total_contacts"] == 0:
            reasons.append("No contacts found - may require additional prospecting")
        
        # Data quality reasons
        quality = scoring_factors["data_quality"]
        quality_score = 0
        for key, value in quality.items():
            if key != "final_score" and value:
                quality_score += 1
        
        if quality_score >= 4:
            reasons.append("High data quality with complete company information")
        elif quality_score <= 2:
            reasons.append("Limited data quality - may need enrichment")
        
        return reasons
    
    def _generate_recommendations(self, company: Company, total_score: float) -> str:
        """Generate AI-powered recommendations based on the score."""
        recommendations = []
        
        if total_score >= 80:
            recommendations.append("High-priority lead - prioritize for immediate outreach")
            recommendations.append("Consider direct executive outreach given strong fit")
        elif total_score >= 60:
            recommendations.append("Qualified lead - include in regular nurturing campaign")
            recommendations.append("Consider industry-specific messaging approach")
        else:
            recommendations.append("Lower priority - may benefit from additional enrichment")
            recommendations.append("Consider automated nurturing sequence first")
        
        # Specific recommendations based on factors
        employee_count = self._get_employee_count(company)
        if 100 <= employee_count <= 500:
            recommendations.append("Optimal size for group health insurance - emphasize cost savings")
        
        if not company.contacts:
            recommendations.append("High priority: Find decision-maker contacts before outreach")
        
        if not company.website:
            recommendations.append("Research company website and online presence")
        
        return " | ".join(recommendations)
    
    def batch_score_companies(
        self, 
        session: Session, 
        company_ids: List[UUID] = None,
        limit: int = 100
    ) -> List[LeadScore]:
        """
        Batch score multiple companies efficiently.
        
        Args:
            session: Database session
            company_ids: Specific company IDs to score (optional)
            limit: Maximum number of companies to score
        
        Returns:
            List of LeadScore instances
        """
        query = session.query(Company)
        
        if company_ids:
            query = query.filter(Company.id.in_(company_ids))
        else:
            # Score companies that haven't been scored recently
            query = query.outerjoin(LeadScore).filter(
                (LeadScore.created_at.is_(None)) |
                (LeadScore.created_at < datetime.utcnow() - timedelta(days=7))
            )
        
        companies = query.limit(limit).all()
        
        lead_scores = []
        for company in companies:
            try:
                # Eager load contacts
                contacts = session.query(Contact).filter(Contact.company_id == company.id).all()
                
                lead_score = self.calculate_score(company, contacts)
                lead_scores.append(lead_score)
                
                # Update company's lead_score field
                company.lead_score = lead_score.total_score
                
            except Exception as e:
                self.logger.error(f"Error scoring company {company.id}: {str(e)}")
                continue
        
        return lead_scores
    
    def get_scoring_analytics(self, session: Session) -> Dict[str, Any]:
        """Get analytics on scoring performance and distribution."""
        
        # Score distribution
        score_distribution = session.query(
            func.count(LeadScore.id).label('count'),
            func.avg(LeadScore.total_score).label('avg_score'),
            LeadScore.score_grade
        ).group_by(LeadScore.score_grade).all()
        
        # Industry performance
        industry_performance = session.query(
            func.count(LeadScore.id).label('count'),
            func.avg(LeadScore.total_score).label('avg_score'),
            LeadScore.industry_risk_level
        ).group_by(LeadScore.industry_risk_level).all()
        
        # Size category performance
        size_performance = session.query(
            func.count(LeadScore.id).label('count'),
            func.avg(LeadScore.total_score).label('avg_score'),
            LeadScore.size_category
        ).group_by(LeadScore.size_category).all()
        
        return {
            "score_distribution": [
                {"grade": row.score_grade, "count": row.count, "avg_score": float(row.avg_score or 0)}
                for row in score_distribution
            ],
            "industry_performance": [
                {"risk_level": row.industry_risk_level, "count": row.count, "avg_score": float(row.avg_score or 0)}
                for row in industry_performance
            ],
            "size_performance": [
                {"category": row.size_category, "count": row.count, "avg_score": float(row.avg_score or 0)}
                for row in size_performance
            ],
        }