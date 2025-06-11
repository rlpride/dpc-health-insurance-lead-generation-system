# Lead Scoring Algorithm Documentation

This document provides comprehensive information about the DPC Health Insurance lead scoring algorithm, including configuration, usage, and A/B testing capabilities.

## Overview

The lead scoring algorithm evaluates companies on a 0-100 scale based on:
1. **Industry (NAICS code)** - 40% weight by default
2. **Company size (employee count)** - 30% weight by default  
3. **Decision-maker contacts found** - 20% weight by default
4. **Data quality** - 10% weight by default

### Key Features

- ✅ **Configurable industry weights** with NAICS code support
- ✅ **Employee size bonuses** for optimal ranges (100-500 employees)
- ✅ **Contact scoring** based on decision-maker availability
- ✅ **A/B testing framework** for algorithm optimization
- ✅ **Batch processing** capabilities
- ✅ **Analytics and reporting** tools

## Quick Start

### 1. Score Companies

```bash
# Score all companies that need scoring (limit 100)
python scripts/score_leads.py score --limit 100

# Score specific companies
python scripts/score_leads.py score --company-ids uuid1 uuid2 uuid3

# Use custom configuration
python scripts/score_leads.py score --config config/examples/lead_scoring_config.json

# Use specific algorithm variant
python scripts/score_leads.py score --variant control --limit 50
```

### 2. View Analytics

```bash
# Get overall scoring analytics
python scripts/score_leads.py analytics

# Get analytics for specific date range
python scripts/score_leads.py analytics --start-date 2024-01-01 --end-date 2024-01-31
```

### 3. Run A/B Test

```bash
# Create A/B test
python scripts/score_leads.py create-test "Contact Weight Test" "Testing contact scoring optimization" config/examples/ab_test_config.json

# Analyze A/B test results
python scripts/score_leads.py analyze-test "Contact Weight Test" 2024-01-01 --end-date 2024-01-31 --confidence 0.95
```

## Scoring Components

### Industry Scoring (40% default weight)

Companies are scored based on their NAICS industry code with configurable weights:

| Industry | NAICS | Base Score | Weight | Risk Level |
|----------|-------|------------|--------|------------|
| Healthcare Services | 621 | 85 | 1.8x | Low |
| Hospitals | 622 | 80 | 1.7x | Low |
| Professional Services | 541 | 70 | 1.4x | Low |
| Manufacturing | 31-33 | 65 | 1.2x | Medium |
| Construction | 23 | 45 | 0.9x | High |
| Retail Trade | 44-45 | 40 | 0.8x | High |

**Configuration Example:**
```json
{
  "industry_weights": {
    "621": {
      "naics_code": "621",
      "weight": 1.8,
      "base_score": 85,
      "risk_level": "low",
      "description": "Ambulatory Health Care Services"
    }
  }
}
```

### Employee Size Scoring (30% default weight)

Companies get scored based on employee count with bonus points for optimal ranges:

| Size Range | Base Score | Bonus | Category | Notes |
|------------|------------|-------|----------|-------|
| 1-10 | 20 | 0 | Micro | Too small |
| 11-50 | 40 | 0 | Small | Limited budget |
| 51-100 | 60 | 0 | Small-Medium | Growing |
| **101-250** | **85** | **+15** | **Medium** | **Optimal** |
| **251-500** | **80** | **+10** | **Medium-Large** | **Optimal** |
| 501-1000 | 70 | 0 | Large | Complex decisions |
| 1001+ | 50 | 0 | Enterprise | Very complex |

**Bonus Logic:**
- Companies with 100-500 employees get additional bonus points
- This range is considered optimal for group health insurance

### Contact Scoring (20% default weight)

Points awarded based on decision-maker contacts found:

| Contact Type | Base Points | Bonus Conditions |
|--------------|-------------|------------------|
| Decision Maker | 10 | Per contact |
| Executive (C-level, VP) | +5 | Additional bonus |
| HR/Benefits Contact | +8 | High value for insurance |
| Verified Email | +3 | Per verified contact |
| Multiple Contacts | +5 | When 3+ contacts found |

**Maximum Contact Score:** 30 points (configurable)

### Data Quality Scoring (10% default weight)

Points for data completeness and freshness:

| Data Element | Points |
|--------------|--------|
| Website URL | 5 |
| Phone Number | 5 |
| Email Domain | 3 |
| Complete Address | 3 |
| EIN/Tax ID | 2 |
| Recent Update (30 days) | 2 |

**Maximum Data Quality Score:** 20 points

## Configuration

### Industry Configuration

Customize industry weights in `config/lead_scoring.py` or via JSON:

```json
{
  "industry_weights": {
    "YOUR_NAICS": {
      "naics_code": "YOUR_NAICS",
      "weight": 1.5,
      "base_score": 75,
      "risk_level": "low",
      "description": "Your Industry Description"
    }
  }
}
```

### Employee Size Configuration

Customize size ranges and bonuses:

```json
{
  "employee_size": {
    "ranges": {
      "101-250": {"score": 85, "bonus": 15, "category": "medium"}
    },
    "optimal_min": 100,
    "optimal_max": 500,
    "bonus_points": 15
  }
}
```

### Contact Scoring Configuration

Adjust contact scoring weights:

```json
{
  "contact_scoring": {
    "decision_maker_base_points": 10,
    "executive_bonus_points": 5,
    "hr_benefits_bonus_points": 8,
    "verified_email_bonus": 3,
    "multiple_contacts_bonus": 5,
    "max_contact_score": 30
  }
}
```

## A/B Testing

### Setting Up A/B Tests

1. **Create test configuration** (see `config/examples/ab_test_config.json`)
2. **Enable A/B testing** in your lead scoring config
3. **Run the test** for sufficient duration
4. **Analyze results** using the CLI

### Example A/B Test Setup

```json
{
  "ab_testing": {
    "enabled": true,
    "test_name": "contact_weight_test",
    "variant_weights": {
      "control": 0.5,
      "variant_a": 0.5
    },
    "algorithm_variants": {
      "control": {
        "version": "1.0",
        "industry_weight": 0.4,
        "size_weight": 0.3,
        "contact_weight": 0.2,
        "data_quality_weight": 0.1
      },
      "variant_a": {
        "version": "1.1",
        "industry_weight": 0.35,
        "size_weight": 0.25,
        "contact_weight": 0.35,
        "data_quality_weight": 0.05
      }
    }
  }
}
```

### A/B Test Analysis

The system provides:
- **Statistical significance testing**
- **Conversion rate analysis**
- **Industry/size performance breakdown**
- **Daily trend analysis**
- **Recommendations** for implementation

## Programmatic Usage

### Using the LeadScoringService

```python
from utils.lead_scoring import LeadScoringService
from config.lead_scoring import LeadScoringConfig
from models.company import Company

# Initialize service
config = LeadScoringConfig()
scoring_service = LeadScoringService(config)

# Score a single company
company = session.query(Company).first()
lead_score = scoring_service.calculate_score(company)

# Batch score companies
lead_scores = scoring_service.batch_score_companies(session, limit=100)
```

### Using A/B Testing

```python
from utils.ab_testing import ABTestTracker
from datetime import datetime

# Initialize tracker
ab_tracker = ABTestTracker()

# Analyze test results
results = ab_tracker.analyze_test_results(
    session,
    test_name="Contact Weight Test",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31)
)

print(f"Winning variant: {results.winning_variant}")
print(f"Lift: {results.lift_percentage}%")
print(f"Recommendation: {results.recommendation}")
```

## Score Interpretation

### Score Ranges
- **90-100 (A+/A):** Highest priority leads
- **80-89 (A-/B+):** High-quality leads
- **60-79 (B/B-):** Medium-quality leads
- **40-59 (C+/C):** Lower priority leads
- **0-39 (C-/D):** Poor fit leads

### Grade Calculation
```python
def calculate_grade(score: int) -> str:
    if score >= 95: return "A+"
    elif score >= 90: return "A"
    elif score >= 85: return "A-"
    elif score >= 80: return "B+"
    elif score >= 75: return "B"
    elif score >= 70: return "B-"
    elif score >= 65: return "C+"
    elif score >= 60: return "C"
    elif score >= 55: return "C-"
    else: return "D"
```

## Best Practices

### 1. Regular Re-scoring
- Re-score companies when new data is available
- Schedule weekly batch scoring for updated companies
- Consider re-scoring after major algorithm changes

### 2. A/B Testing Guidelines
- Run tests for at least 2-4 weeks
- Ensure minimum sample size of 100+ companies per variant
- Test one variable at a time for clear results
- Monitor both primary and secondary metrics

### 3. Configuration Management
- Version control your configuration changes
- Document the rationale for weight adjustments
- Test configuration changes in staging first
- Monitor performance after deploying changes

### 4. Data Quality
- Regularly audit and improve data completeness
- Verify contact information accuracy
- Keep NAICS codes updated and accurate
- Monitor for data freshness

## Troubleshooting

### Common Issues

**Low Scores Across All Companies**
- Check industry weight configuration
- Verify NAICS code mapping
- Review employee count data quality

**Inconsistent A/B Test Results**
- Ensure sufficient sample size
- Check for data quality issues
- Verify proper variant assignment

**Poor Contact Scores**
- Validate decision-maker detection logic
- Check email verification status
- Review contact data completeness

### Monitoring

Monitor these key metrics:
- Average score distribution
- High-quality lead percentage
- Score stability over time
- A/B test performance
- Data quality metrics

## API Integration

The scoring algorithm integrates with:
- **Apollo.io** for contact enrichment
- **Proxycurl** for LinkedIn data
- **Pipedrive** for CRM sync
- **Dropcontact** for email verification

Scores are automatically updated when new contact data is enriched.

## Support

For technical support or questions:
1. Check the logs in `lead_scoring.log`
2. Review configuration files for syntax errors
3. Validate database connectivity
4. Check API rate limits and quotas

---

*Last updated: January 2024*