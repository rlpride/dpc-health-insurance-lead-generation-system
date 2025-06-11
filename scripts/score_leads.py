#!/usr/bin/env python3
"""CLI script for lead scoring with A/B testing capabilities."""

import argparse
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import get_settings
from config.lead_scoring import LeadScoringConfig
from utils.lead_scoring import LeadScoringService
from utils.ab_testing import ABTestTracker
from models.base import Base
from models.company import Company
from models.contact import Contact
from models.lead_score import LeadScore


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('lead_scoring.log')
        ]
    )


def get_database_session():
    """Get database session."""
    settings = get_settings()
    engine = create_engine(str(settings.database_url))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def score_companies(
    company_ids: Optional[List[str]] = None,
    limit: int = 100,
    algorithm_variant: Optional[str] = None,
    config_file: Optional[str] = None
) -> None:
    """Score companies using the lead scoring algorithm."""
    
    # Load configuration
    if config_file:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        config = LeadScoringConfig(**config_data)
    else:
        config = LeadScoringConfig()
    
    # Initialize scoring service
    scoring_service = LeadScoringService(config)
    
    # Get database session
    session = get_database_session()
    
    try:
        if company_ids:
            # Score specific companies
            uuid_company_ids = [uuid.UUID(cid) for cid in company_ids]
            lead_scores = scoring_service.batch_score_companies(
                session, 
                company_ids=uuid_company_ids,
                limit=limit
            )
        else:
            # Score companies that need scoring
            lead_scores = scoring_service.batch_score_companies(
                session,
                limit=limit
            )
        
        # Save results
        for lead_score in lead_scores:
            session.add(lead_score)
        
        session.commit()
        
        print(f"Successfully scored {len(lead_scores)} companies")
        
        # Print summary statistics
        if lead_scores:
            avg_score = sum(ls.total_score for ls in lead_scores) / len(lead_scores)
            high_quality = sum(1 for ls in lead_scores if ls.is_high_quality)
            medium_quality = sum(1 for ls in lead_scores if ls.is_medium_quality)
            
            print(f"\nScoring Summary:")
            print(f"  Average Score: {avg_score:.1f}")
            print(f"  High Quality Leads: {high_quality} ({high_quality/len(lead_scores)*100:.1f}%)")
            print(f"  Medium Quality Leads: {medium_quality} ({medium_quality/len(lead_scores)*100:.1f}%)")
            
            # Show top 5 companies by score
            top_companies = sorted(lead_scores, key=lambda x: x.total_score, reverse=True)[:5]
            print(f"\nTop 5 Companies by Score:")
            for i, ls in enumerate(top_companies, 1):
                company = session.query(Company).filter(Company.id == ls.company_id).first()
                print(f"  {i}. {company.name} - Score: {ls.total_score} ({ls.score_grade})")
    
    except Exception as e:
        session.rollback()
        print(f"Error scoring companies: {str(e)}")
        raise
    finally:
        session.close()


def create_ab_test(
    test_name: str,
    description: str,
    config_file: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> None:
    """Create a new A/B test."""
    
    # Load test configuration
    with open(config_file, 'r') as f:
        test_config = json.load(f)
    
    # Parse dates
    start_dt = datetime.fromisoformat(start_date) if start_date else datetime.utcnow()
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    # Initialize A/B test tracker
    ab_tracker = ABTestTracker()
    
    # Create test
    test = ab_tracker.create_test(
        test_name=test_name,
        description=description,
        variant_configs=test_config["variants"],
        traffic_split=test_config["traffic_split"],
        start_date=start_dt,
        end_date=end_dt,
        success_metric=test_config.get("success_metric", "conversion_rate")
    )
    
    # Save test configuration
    test_file = f"ab_test_{test_name.lower().replace(' ', '_')}.json"
    with open(test_file, 'w') as f:
        json.dump(test, f, indent=2, default=str)
    
    print(f"Created A/B test: {test_name}")
    print(f"Configuration saved to: {test_file}")


def analyze_ab_test(
    test_name: str,
    start_date: str,
    end_date: Optional[str] = None,
    confidence_level: float = 0.95
) -> None:
    """Analyze A/B test results."""
    
    # Parse dates
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
    
    # Initialize A/B test tracker
    ab_tracker = ABTestTracker()
    
    # Get database session
    session = get_database_session()
    
    try:
        # Analyze test results
        results = ab_tracker.analyze_test_results(
            session,
            test_name,
            start_dt,
            end_dt,
            confidence_level
        )
        
        # Print results
        print(f"\nA/B Test Analysis: {test_name}")
        print(f"Period: {start_dt.date()} to {end_dt.date()}")
        print(f"Confidence Level: {confidence_level*100}%")
        print(f"Statistical Significance: {'Yes' if results.is_significant else 'No'}")
        
        if results.winning_variant:
            print(f"Winning Variant: {results.winning_variant}")
        if results.lift_percentage:
            print(f"Lift: {results.lift_percentage:.2f}%")
        
        print(f"\nRecommendation: {results.recommendation}")
        
        # Print variant statistics
        print(f"\nVariant Performance:")
        for variant, stats in results.variant_stats.items():
            print(f"  {variant}:")
            print(f"    Sample Size: {stats['sample_size']}")
            print(f"    Average Score: {stats['avg_score']:.1f}")
            print(f"    High Quality Rate: {stats['high_quality_rate']*100:.1f}%")
            print(f"    Conversion Rate: {stats['conversion_rate']*100:.1f}%")
        
        # Get detailed performance metrics
        metrics = ab_tracker.get_test_performance_metrics(
            session, test_name, start_dt, end_dt
        )
        
        # Save detailed results
        results_file = f"ab_test_results_{test_name.lower().replace(' ', '_')}.json"
        with open(results_file, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: {results_file}")
    
    except Exception as e:
        print(f"Error analyzing A/B test: {str(e)}")
        raise
    finally:
        session.close()


def get_scoring_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> None:
    """Get lead scoring analytics."""
    
    # Initialize scoring service
    scoring_service = LeadScoringService()
    
    # Get database session
    session = get_database_session()
    
    try:
        # Get analytics
        analytics = scoring_service.get_scoring_analytics(session)
        
        print("Lead Scoring Analytics")
        print("=" * 50)
        
        # Score distribution
        print("\nScore Distribution by Grade:")
        for grade_info in analytics["score_distribution"]:
            print(f"  Grade {grade_info['grade']}: {grade_info['count']} companies "
                  f"(avg: {grade_info['avg_score']:.1f})")
        
        # Industry performance
        print("\nIndustry Performance by Risk Level:")
        for industry_info in analytics["industry_performance"]:
            print(f"  {industry_info['risk_level'].title()} Risk: {industry_info['count']} companies "
                  f"(avg: {industry_info['avg_score']:.1f})")
        
        # Size performance
        print("\nSize Category Performance:")
        for size_info in analytics["size_performance"]:
            print(f"  {size_info['category'].title()}: {size_info['count']} companies "
                  f"(avg: {size_info['avg_score']:.1f})")
        
        # Additional statistics
        total_scored = session.query(LeadScore).count()
        recent_scored = session.query(LeadScore).filter(
            LeadScore.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        print(f"\nOverall Statistics:")
        print(f"  Total Companies Scored: {total_scored}")
        print(f"  Scored in Last 7 Days: {recent_scored}")
    
    except Exception as e:
        print(f"Error getting analytics: {str(e)}")
        raise
    finally:
        session.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Lead Scoring CLI with A/B Testing")
    
    # Add verbosity option
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    # Create subparsers
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Score companies command
    score_parser = subparsers.add_parser("score", help="Score companies")
    score_parser.add_argument(
        "--company-ids",
        nargs="+",
        help="Specific company IDs to score"
    )
    score_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of companies to score"
    )
    score_parser.add_argument(
        "--variant",
        help="Algorithm variant to use"
    )
    score_parser.add_argument(
        "--config",
        help="Path to scoring configuration file"
    )
    
    # Create A/B test command
    ab_create_parser = subparsers.add_parser("create-test", help="Create A/B test")
    ab_create_parser.add_argument("test_name", help="Name of the test")
    ab_create_parser.add_argument("description", help="Description of the test")
    ab_create_parser.add_argument("config_file", help="Path to test configuration file")
    ab_create_parser.add_argument("--start-date", help="Start date (ISO format)")
    ab_create_parser.add_argument("--end-date", help="End date (ISO format)")
    
    # Analyze A/B test command
    ab_analyze_parser = subparsers.add_parser("analyze-test", help="Analyze A/B test")
    ab_analyze_parser.add_argument("test_name", help="Name of the test")
    ab_analyze_parser.add_argument("start_date", help="Start date (ISO format)")
    ab_analyze_parser.add_argument("--end-date", help="End date (ISO format)")
    ab_analyze_parser.add_argument(
        "--confidence",
        type=float,
        default=0.95,
        help="Confidence level for significance testing"
    )
    
    # Analytics command
    analytics_parser = subparsers.add_parser("analytics", help="Get scoring analytics")
    analytics_parser.add_argument("--start-date", help="Start date (ISO format)")
    analytics_parser.add_argument("--end-date", help="End date (ISO format)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level)
    
    # Execute command
    try:
        if args.command == "score":
            score_companies(
                company_ids=args.company_ids,
                limit=args.limit,
                algorithm_variant=args.variant,
                config_file=args.config
            )
        elif args.command == "create-test":
            create_ab_test(
                test_name=args.test_name,
                description=args.description,
                config_file=args.config_file,
                start_date=args.start_date,
                end_date=args.end_date
            )
        elif args.command == "analyze-test":
            analyze_ab_test(
                test_name=args.test_name,
                start_date=args.start_date,
                end_date=args.end_date,
                confidence_level=args.confidence
            )
        elif args.command == "analytics":
            get_scoring_analytics(
                start_date=args.start_date,
                end_date=args.end_date
            )
        else:
            parser.print_help()
    
    except Exception as e:
        logging.error(f"Command failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()