"""Worker for calculating lead scores for companies."""

import logging
from typing import Dict, Any
from datetime import datetime

from workers.base_worker import BaseWorker
from models import Company, LeadScore, get_db_session

logger = logging.getLogger(__name__)


class ScoringWorker(BaseWorker):
    """Worker that calculates lead scores for enriched companies."""
    
    @property
    def worker_name(self) -> str:
        return "scoring_worker"
    
    @property
    def queue_name(self) -> str:
        return "companies.to_score"
    
    def process_message(self, body: Dict[str, Any]) -> bool:
        """Process scoring request for a company."""
        try:
            company_id = body.get("company_id")
            if not company_id:
                logger.error("No company_id in message")
                return False
            
            # Calculate and save score
            with get_db_session() as db:
                company = db.query(Company).filter_by(id=company_id).first()
                if not company:
                    logger.error(f"Company {company_id} not found")
                    return False
                
                # Calculate score
                score_data = self.calculate_score(company)
                
                # Save score history
                lead_score = LeadScore(
                    company_id=company.id,
                    total_score=score_data["total_score"],
                    score_grade=LeadScore.calculate_grade(score_data["total_score"]),
                    industry_score=score_data["industry_score"],
                    size_score=score_data["size_score"],
                    location_score=score_data["location_score"],
                    data_quality_score=score_data["data_quality_score"],
                    scoring_factors=score_data["factors"],
                    created_by=self.worker_id
                )
                db.add(lead_score)
                
                # Update company with latest score
                company.lead_score = score_data["total_score"]
                
                # If high-quality lead, send to CRM sync
                if score_data["total_score"] >= self.settings.high_score_threshold:
                    self.publish_message(
                        {"company_id": str(company_id)},
                        "companies.to_sync.tasks"
                    )
                
                db.commit()
                logger.info(f"Scored company {company_id}: {score_data['total_score']}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error processing scoring: {str(e)}")
            return False
    
    def calculate_score(self, company: Company) -> Dict[str, Any]:
        """Calculate lead score for a company."""
        # Placeholder scoring algorithm
        scores = {
            "industry_score": 70,
            "size_score": 80,
            "location_score": 75,
            "data_quality_score": 85,
        }
        
        total_score = sum(scores.values()) // len(scores)
        
        return {
            "total_score": total_score,
            **scores,
            "factors": {
                "naics_code": company.naics_code,
                "employee_count": company.employee_count_min,
                "state": company.state,
                "has_contacts": len(company.contacts) > 0
            }
        } 