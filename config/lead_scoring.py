"""Lead scoring configuration and industry weights."""

from typing import Dict, Any, List
from pydantic import BaseModel, Field


class IndustryWeight(BaseModel):
    """Industry weight configuration for NAICS codes."""
    
    naics_code: str = Field(description="NAICS code (2-6 digits)")
    weight: float = Field(ge=0.0, le=2.0, description="Scoring weight multiplier")
    base_score: int = Field(ge=0, le=100, description="Base score for this industry")
    risk_level: str = Field(description="Risk level: low, medium, high")
    description: str = Field(description="Industry description")


class EmployeeSizeConfig(BaseModel):
    """Employee size scoring configuration."""
    
    ranges: Dict[str, Dict[str, Any]] = Field(
        default={
            "1-10": {"score": 20, "bonus": 0, "category": "micro"},
            "11-50": {"score": 40, "bonus": 0, "category": "small"},
            "51-100": {"score": 60, "bonus": 0, "category": "small-medium"},
            "101-250": {"score": 85, "bonus": 15, "category": "medium"},  # Bonus range
            "251-500": {"score": 80, "bonus": 10, "category": "medium-large"},  # Bonus range
            "501-1000": {"score": 70, "bonus": 0, "category": "large"},
            "1001-5000": {"score": 50, "bonus": 0, "category": "enterprise"},
            "5000+": {"score": 30, "bonus": 0, "category": "mega"},
        }
    )
    
    optimal_min: int = Field(default=100, description="Optimal employee count minimum")
    optimal_max: int = Field(default=500, description="Optimal employee count maximum")
    bonus_points: int = Field(default=15, description="Bonus points for optimal range")


class ContactScoringConfig(BaseModel):
    """Configuration for contact-based scoring."""
    
    decision_maker_base_points: int = Field(default=10, description="Base points per decision maker")
    executive_bonus_points: int = Field(default=5, description="Bonus for executive contacts")
    hr_benefits_bonus_points: int = Field(default=8, description="Bonus for HR/benefits contacts")
    verified_email_bonus: int = Field(default=3, description="Bonus for verified email")
    multiple_contacts_bonus: int = Field(default=5, description="Bonus for 3+ contacts")
    max_contact_score: int = Field(default=30, description="Maximum score from contacts")


class ABTestConfig(BaseModel):
    """A/B testing configuration for scoring algorithms."""
    
    enabled: bool = Field(default=False, description="Enable A/B testing")
    test_name: str = Field(default="", description="Name of current test")
    variant_weights: Dict[str, float] = Field(
        default={"control": 0.5, "variant_a": 0.5},
        description="Weight distribution for variants"
    )
    algorithm_variants: Dict[str, Dict[str, Any]] = Field(
        default={
            "control": {
                "version": "1.0",
                "industry_weight": 0.4,
                "size_weight": 0.3,
                "contact_weight": 0.2,
                "data_quality_weight": 0.1,
            },
            "variant_a": {
                "version": "1.1",
                "industry_weight": 0.35,
                "size_weight": 0.25,
                "contact_weight": 0.3,
                "data_quality_weight": 0.1,
            }
        }
    )


class LeadScoringConfig(BaseModel):
    """Main lead scoring configuration."""
    
    # Industry configurations
    industry_weights: Dict[str, IndustryWeight] = Field(
        default={
            # Healthcare industries (high priority for health insurance)
            "621": IndustryWeight(
                naics_code="621",
                weight=1.8,
                base_score=85,
                risk_level="low",
                description="Ambulatory Health Care Services"
            ),
            "622": IndustryWeight(
                naics_code="622",
                weight=1.7,
                base_score=80,
                risk_level="low",
                description="Hospitals"
            ),
            "623": IndustryWeight(
                naics_code="623",
                weight=1.6,
                base_score=75,
                risk_level="medium",
                description="Nursing and Residential Care Facilities"
            ),
            
            # Professional services (medium-high priority)
            "541": IndustryWeight(
                naics_code="541",
                weight=1.4,
                base_score=70,
                risk_level="low",
                description="Professional, Scientific, and Technical Services"
            ),
            "551": IndustryWeight(
                naics_code="551",
                weight=1.3,
                base_score=68,
                risk_level="low",
                description="Management of Companies and Enterprises"
            ),
            
            # Manufacturing (medium priority)
            "31": IndustryWeight(
                naics_code="31",
                weight=1.2,
                base_score=65,
                risk_level="medium",
                description="Manufacturing"
            ),
            "32": IndustryWeight(
                naics_code="32",
                weight=1.2,
                base_score=65,
                risk_level="medium",
                description="Manufacturing"
            ),
            "33": IndustryWeight(
                naics_code="33",
                weight=1.2,
                base_score=65,
                risk_level="medium",
                description="Manufacturing"
            ),
            
            # Finance and Insurance (medium priority)
            "52": IndustryWeight(
                naics_code="52",
                weight=1.1,
                base_score=60,
                risk_level="medium",
                description="Finance and Insurance"
            ),
            
            # Technology (medium priority)
            "518": IndustryWeight(
                naics_code="518",
                weight=1.3,
                base_score=68,
                risk_level="low",
                description="Data Processing, Hosting, and Related Services"
            ),
            "519": IndustryWeight(
                naics_code="519",
                weight=1.3,
                base_score=68,
                risk_level="low",
                description="Other Information Services"
            ),
            
            # Construction (lower priority due to seasonal nature)
            "23": IndustryWeight(
                naics_code="23",
                weight=0.9,
                base_score=45,
                risk_level="high",
                description="Construction"
            ),
            
            # Retail/Hospitality (lower priority)
            "44": IndustryWeight(
                naics_code="44",
                weight=0.8,
                base_score=40,
                risk_level="high",
                description="Retail Trade"
            ),
            "45": IndustryWeight(
                naics_code="45",
                weight=0.8,
                base_score=40,
                risk_level="high",
                description="Retail Trade"
            ),
            "72": IndustryWeight(
                naics_code="72",
                weight=0.7,
                base_score=35,
                risk_level="high",
                description="Accommodation and Food Services"
            ),
        }
    )
    
    # Default industry config for unknown NAICS codes
    default_industry: IndustryWeight = Field(
        default=IndustryWeight(
            naics_code="unknown",
            weight=1.0,
            base_score=50,
            risk_level="medium",
            description="Unknown Industry"
        )
    )
    
    # Employee size configuration
    employee_size: EmployeeSizeConfig = Field(default_factory=EmployeeSizeConfig)
    
    # Contact scoring configuration
    contact_scoring: ContactScoringConfig = Field(default_factory=ContactScoringConfig)
    
    # A/B testing configuration
    ab_testing: ABTestConfig = Field(default_factory=ABTestConfig)
    
    # Overall scoring weights
    component_weights: Dict[str, float] = Field(
        default={
            "industry_score": 0.4,
            "size_score": 0.3,
            "contact_score": 0.2,
            "data_quality_score": 0.1,
        }
    )
    
    # Data quality scoring
    data_quality_weights: Dict[str, int] = Field(
        default={
            "has_website": 5,
            "has_phone": 5,
            "has_email_domain": 3,
            "has_address": 3,
            "has_ein": 2,
            "recent_data": 2,
        }
    )
    
    def get_industry_weight(self, naics_code: str) -> IndustryWeight:
        """Get industry weight for a NAICS code."""
        if not naics_code:
            return self.default_industry
            
        # Try exact match first
        if naics_code in self.industry_weights:
            return self.industry_weights[naics_code]
        
        # Try progressively shorter codes (e.g., 54111 -> 5411 -> 541 -> 54)
        for length in range(len(naics_code) - 1, 1, -1):
            partial_code = naics_code[:length]
            if partial_code in self.industry_weights:
                return self.industry_weights[partial_code]
        
        return self.default_industry
    
    def get_employee_size_config(self, employee_count: int) -> Dict[str, Any]:
        """Get employee size configuration for a given count."""
        for range_key, config in self.employee_size.ranges.items():
            if self._is_in_range(employee_count, range_key):
                return config
        return self.employee_size.ranges["1-10"]  # Default to smallest range
    
    def _is_in_range(self, count: int, range_str: str) -> bool:
        """Check if employee count is in the specified range."""
        if range_str.endswith("+"):
            min_val = int(range_str[:-1])
            return count >= min_val
        elif "-" in range_str:
            min_val, max_val = map(int, range_str.split("-"))
            return min_val <= count <= max_val
        else:
            return count == int(range_str)