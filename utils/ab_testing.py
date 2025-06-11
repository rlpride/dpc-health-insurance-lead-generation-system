"""A/B testing framework for lead scoring algorithms."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import func, text

from models.company import Company
from models.lead_score import LeadScore
from config.lead_scoring import ABTestConfig


logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Status of A/B test."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ABTestResult:
    """Results of an A/B test comparison."""
    
    test_name: str
    status: TestStatus
    start_date: datetime
    end_date: Optional[datetime]
    
    # Variant performance
    variant_stats: Dict[str, Dict[str, Any]]
    
    # Statistical significance
    is_significant: bool
    confidence_level: float
    p_value: Optional[float]
    
    # Recommendations
    winning_variant: Optional[str]
    lift_percentage: Optional[float]
    recommendation: str


class ABTestTracker:
    """Tracker for A/B testing lead scoring algorithms."""
    
    def __init__(self):
        """Initialize the A/B test tracker."""
        self.logger = logger
    
    def create_test(
        self,
        test_name: str,
        description: str,
        variant_configs: Dict[str, Dict[str, Any]],
        traffic_split: Dict[str, float],
        start_date: datetime = None,
        end_date: datetime = None,
        success_metric: str = "conversion_rate"
    ) -> Dict[str, Any]:
        """
        Create a new A/B test configuration.
        
        Args:
            test_name: Name of the test
            description: Description of what's being tested
            variant_configs: Configuration for each variant
            traffic_split: Traffic split between variants (should sum to 1.0)
            start_date: When to start the test
            end_date: When to end the test
            success_metric: Primary metric to optimize for
        
        Returns:
            Test configuration dictionary
        """
        if abs(sum(traffic_split.values()) - 1.0) > 0.01:
            raise ValueError("Traffic split must sum to 1.0")
        
        test_config = {
            "test_name": test_name,
            "description": description,
            "status": TestStatus.DRAFT.value,
            "variant_configs": variant_configs,
            "traffic_split": traffic_split,
            "start_date": start_date or datetime.utcnow(),
            "end_date": end_date,
            "success_metric": success_metric,
            "created_at": datetime.utcnow(),
            "participants": 0,
            "conversions": {variant: 0 for variant in variant_configs.keys()},
        }
        
        self.logger.info(f"Created A/B test: {test_name}")
        return test_config
    
    def get_variant_assignment(self, company_id: UUID, test_config: Dict[str, Any]) -> str:
        """
        Get variant assignment for a company in an A/B test.
        
        Args:
            company_id: Company ID
            test_config: Test configuration
        
        Returns:
            Variant name
        """
        import hashlib
        
        # Use company ID hash for consistent assignment
        hash_input = f"{test_config['test_name']}_{company_id}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        
        # Determine variant based on traffic split
        normalized_hash = (hash_value % 1000) / 1000.0  # 0.0 to 1.0
        
        cumulative_weight = 0.0
        for variant, weight in test_config["traffic_split"].items():
            cumulative_weight += weight
            if normalized_hash <= cumulative_weight:
                return variant
        
        # Fallback to first variant
        return list(test_config["variant_configs"].keys())[0]
    
    def analyze_test_results(
        self,
        session: Session,
        test_name: str,
        start_date: datetime,
        end_date: datetime = None,
        confidence_level: float = 0.95
    ) -> ABTestResult:
        """
        Analyze A/B test results and determine statistical significance.
        
        Args:
            session: Database session
            test_name: Name of the test to analyze
            start_date: Start date of the test
            end_date: End date of the test (default: now)
            confidence_level: Confidence level for significance testing
        
        Returns:
            ABTestResult with analysis
        """
        end_date = end_date or datetime.utcnow()
        
        # Get lead scores for the test period
        lead_scores = session.query(LeadScore).filter(
            LeadScore.created_at >= start_date,
            LeadScore.created_at <= end_date,
            LeadScore.created_by.like(f"algorithm_%")
        ).all()
        
        # Group by variant
        variant_data = {}
        for score in lead_scores:
            variant = score.created_by.replace("algorithm_", "")
            if variant not in variant_data:
                variant_data[variant] = []
            variant_data[variant].append(score)
        
        # Calculate statistics for each variant
        variant_stats = {}
        for variant, scores in variant_data.items():
            if not scores:
                continue
            
            total_scores = [s.total_score for s in scores]
            high_quality_leads = [s for s in scores if s.is_high_quality]
            medium_quality_leads = [s for s in scores if s.is_medium_quality]
            
            variant_stats[variant] = {
                "sample_size": len(scores),
                "avg_score": sum(total_scores) / len(total_scores),
                "median_score": sorted(total_scores)[len(total_scores) // 2],
                "high_quality_rate": len(high_quality_leads) / len(scores),
                "medium_quality_rate": len(medium_quality_leads) / len(scores),
                "conversion_rate": len(high_quality_leads) / len(scores),  # Using high quality as conversion
                "score_distribution": self._calculate_score_distribution(total_scores),
            }
        
        # Determine statistical significance and winning variant
        is_significant, p_value, winning_variant, lift = self._calculate_significance(
            variant_stats, confidence_level
        )
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            variant_stats, is_significant, winning_variant, lift
        )
        
        return ABTestResult(
            test_name=test_name,
            status=TestStatus.RUNNING,
            start_date=start_date,
            end_date=end_date,
            variant_stats=variant_stats,
            is_significant=is_significant,
            confidence_level=confidence_level,
            p_value=p_value,
            winning_variant=winning_variant,
            lift_percentage=lift,
            recommendation=recommendation,
        )
    
    def get_test_performance_metrics(
        self,
        session: Session,
        test_name: str,
        start_date: datetime,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Get detailed performance metrics for an A/B test.
        
        Args:
            session: Database session
            test_name: Name of the test
            start_date: Start date of the test
            end_date: End date of the test
        
        Returns:
            Dictionary with detailed metrics
        """
        end_date = end_date or datetime.utcnow()
        
        # Get conversion funnel data
        funnel_data = self._get_conversion_funnel(session, start_date, end_date)
        
        # Get industry performance by variant
        industry_performance = self._get_industry_performance_by_variant(
            session, start_date, end_date
        )
        
        # Get size category performance by variant
        size_performance = self._get_size_performance_by_variant(
            session, start_date, end_date
        )
        
        # Get daily performance trends
        daily_trends = self._get_daily_performance_trends(
            session, start_date, end_date
        )
        
        return {
            "test_name": test_name,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "duration_days": (end_date - start_date).days,
            },
            "conversion_funnel": funnel_data,
            "industry_performance": industry_performance,
            "size_performance": size_performance,
            "daily_trends": daily_trends,
        }
    
    def _calculate_score_distribution(self, scores: List[int]) -> Dict[str, int]:
        """Calculate score distribution by grade."""
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0}
        
        for score in scores:
            if score >= 90:
                distribution["A"] += 1
            elif score >= 80:
                distribution["B"] += 1
            elif score >= 60:
                distribution["C"] += 1
            else:
                distribution["D"] += 1
        
        return distribution
    
    def _calculate_significance(
        self,
        variant_stats: Dict[str, Dict[str, Any]],
        confidence_level: float
    ) -> Tuple[bool, Optional[float], Optional[str], Optional[float]]:
        """
        Calculate statistical significance between variants.
        
        This is a simplified implementation. In production, you'd want to use
        proper statistical libraries like scipy.stats.
        """
        if len(variant_stats) < 2:
            return False, None, None, None
        
        # Get control and variant (assumes first two variants)
        variants = list(variant_stats.keys())
        control = variants[0]
        variant = variants[1]
        
        control_stats = variant_stats[control]
        variant_stats_data = variant_stats[variant]
        
        # Check minimum sample size
        if control_stats["sample_size"] < 30 or variant_stats_data["sample_size"] < 30:
            return False, None, None, None
        
        # Calculate conversion rates
        control_rate = control_stats["conversion_rate"]
        variant_rate = variant_stats_data["conversion_rate"]
        
        # Calculate lift
        lift = ((variant_rate - control_rate) / control_rate) * 100 if control_rate > 0 else 0
        
        # Simplified significance test (normally would use proper statistical test)
        # This is a placeholder - use scipy.stats.chi2_contingency in production
        difference = abs(variant_rate - control_rate)
        is_significant = difference > 0.05  # Simplified threshold
        
        winning_variant = variant if variant_rate > control_rate else control
        
        return is_significant, 0.05, winning_variant, lift  # Placeholder p-value
    
    def _generate_recommendation(
        self,
        variant_stats: Dict[str, Dict[str, Any]],
        is_significant: bool,
        winning_variant: Optional[str],
        lift: Optional[float]
    ) -> str:
        """Generate recommendation based on test results."""
        if not is_significant:
            return "Test is not statistically significant. Continue running or increase sample size."
        
        if not winning_variant or not lift:
            return "Unable to determine winning variant. Review test setup."
        
        if abs(lift) < 5:
            return f"Winning variant: {winning_variant}, but lift is small ({lift:.1f}%). Consider practical significance."
        
        if lift > 0:
            return f"Implement {winning_variant} - shows {lift:.1f}% improvement in conversion rate."
        else:
            return f"Stick with control - {winning_variant} shows {abs(lift):.1f}% decrease in performance."
    
    def _get_conversion_funnel(
        self,
        session: Session,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get conversion funnel data by variant."""
        query = text("""
            SELECT 
                REPLACE(created_by, 'algorithm_', '') as variant,
                COUNT(*) as total_leads,
                SUM(CASE WHEN total_score >= 80 THEN 1 ELSE 0 END) as high_quality_leads,
                SUM(CASE WHEN total_score >= 60 THEN 1 ELSE 0 END) as qualified_leads,
                AVG(total_score) as avg_score
            FROM lead_scores 
            WHERE created_at >= :start_date 
            AND created_at <= :end_date
            AND created_by LIKE 'algorithm_%'
            GROUP BY variant
        """)
        
        results = session.execute(query, {
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        
        funnel_data = {}
        for row in results:
            funnel_data[row.variant] = {
                "total_leads": row.total_leads,
                "qualified_leads": row.qualified_leads,
                "high_quality_leads": row.high_quality_leads,
                "qualification_rate": row.qualified_leads / row.total_leads if row.total_leads > 0 else 0,
                "high_quality_rate": row.high_quality_leads / row.total_leads if row.total_leads > 0 else 0,
                "avg_score": float(row.avg_score) if row.avg_score else 0,
            }
        
        return funnel_data
    
    def _get_industry_performance_by_variant(
        self,
        session: Session,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get industry performance breakdown by variant."""
        query = text("""
            SELECT 
                REPLACE(ls.created_by, 'algorithm_', '') as variant,
                ls.industry_risk_level,
                COUNT(*) as count,
                AVG(ls.total_score) as avg_score,
                SUM(CASE WHEN ls.total_score >= 80 THEN 1 ELSE 0 END) as high_quality_count
            FROM lead_scores ls
            WHERE ls.created_at >= :start_date 
            AND ls.created_at <= :end_date
            AND ls.created_by LIKE 'algorithm_%'
            GROUP BY variant, ls.industry_risk_level
            ORDER BY variant, ls.industry_risk_level
        """)
        
        results = session.execute(query, {
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        
        industry_data = {}
        for row in results:
            if row.variant not in industry_data:
                industry_data[row.variant] = {}
            
            industry_data[row.variant][row.industry_risk_level] = {
                "count": row.count,
                "avg_score": float(row.avg_score) if row.avg_score else 0,
                "high_quality_rate": row.high_quality_count / row.count if row.count > 0 else 0
            }
        
        return industry_data
    
    def _get_size_performance_by_variant(
        self,
        session: Session,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get size category performance by variant."""
        query = text("""
            SELECT 
                REPLACE(ls.created_by, 'algorithm_', '') as variant,
                ls.size_category,
                COUNT(*) as count,
                AVG(ls.total_score) as avg_score,
                SUM(CASE WHEN ls.total_score >= 80 THEN 1 ELSE 0 END) as high_quality_count
            FROM lead_scores ls
            WHERE ls.created_at >= :start_date 
            AND ls.created_at <= :end_date
            AND ls.created_by LIKE 'algorithm_%'
            GROUP BY variant, ls.size_category
            ORDER BY variant, ls.size_category
        """)
        
        results = session.execute(query, {
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        
        size_data = {}
        for row in results:
            if row.variant not in size_data:
                size_data[row.variant] = {}
            
            size_data[row.variant][row.size_category] = {
                "count": row.count,
                "avg_score": float(row.avg_score) if row.avg_score else 0,
                "high_quality_rate": row.high_quality_count / row.count if row.count > 0 else 0
            }
        
        return size_data
    
    def _get_daily_performance_trends(
        self,
        session: Session,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get daily performance trends by variant."""
        query = text("""
            SELECT 
                REPLACE(created_by, 'algorithm_', '') as variant,
                DATE(created_at) as date,
                COUNT(*) as daily_count,
                AVG(total_score) as daily_avg_score,
                SUM(CASE WHEN total_score >= 80 THEN 1 ELSE 0 END) as daily_high_quality
            FROM lead_scores 
            WHERE created_at >= :start_date 
            AND created_at <= :end_date
            AND created_by LIKE 'algorithm_%'
            GROUP BY variant, DATE(created_at)
            ORDER BY date
        """)
        
        results = session.execute(query, {
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        
        trends = {}
        for row in results:
            if row.variant not in trends:
                trends[row.variant] = []
            
            trends[row.variant].append({
                "date": row.date.isoformat(),
                "count": row.daily_count,
                "avg_score": float(row.daily_avg_score) if row.daily_avg_score else 0,
                "high_quality_count": row.daily_high_quality,
                "high_quality_rate": row.daily_high_quality / row.daily_count if row.daily_count > 0 else 0
            })
        
        return trends