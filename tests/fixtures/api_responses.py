"""Mock API response fixtures for testing external services."""

from datetime import datetime
from uuid import uuid4


class MockAPIResponses:
    """Collection of mock API responses for testing."""
    
    @staticmethod
    def apollo_people_search_success():
        """Apollo.io successful people search response."""
        return {
            "people": [
                {
                    "id": "apollo_person_001",
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@healthcorp.com",
                    "email_status": "verified",
                    "title": "Chief Executive Officer",
                    "linkedin_url": "https://linkedin.com/in/johndoe",
                    "twitter_url": None,
                    "github_url": None,
                    "facebook_url": None,
                    "headline": "CEO at HealthCorp Insurance | Transforming Healthcare Coverage",
                    "photo_url": "https://example.com/photo.jpg",
                    "employment_history": [
                        {
                            "organization_id": "org_healthcorp",
                            "organization_name": "HealthCorp Insurance",
                            "title": "Chief Executive Officer",
                            "start_date": "2020-01-01",
                            "end_date": None,
                            "current": True
                        }
                    ],
                    "organization": {
                        "id": "org_healthcorp",
                        "name": "HealthCorp Insurance",
                        "website_url": "https://healthcorp.com",
                        "blog_url": None,
                        "angellist_url": None,
                        "linkedin_url": "https://linkedin.com/company/healthcorp",
                        "twitter_url": "https://twitter.com/healthcorp",
                        "facebook_url": None,
                        "primary_phone": {
                            "number": "+1-555-0123",
                            "source": "Account"
                        },
                        "languages": ["English"],
                        "alexa_ranking": 50000,
                        "phone": "+1-555-0123",
                        "linkedin_uid": "12345",
                        "publicly_traded_symbol": None,
                        "publicly_traded_exchange": None,
                        "logo_url": "https://healthcorp.com/logo.png",
                        "crunchbase_url": None,
                        "primary_domain": "healthcorp.com",
                        "persona_counts": {
                            "engineering": 45,
                            "sales": 32,
                            "marketing": 18,
                            "finance": 12,
                            "operations": 23
                        }
                    },
                    "phone_numbers": [
                        {
                            "raw_number": "+1-555-0199",
                            "sanitized_number": "+15550199",
                            "type": "mobile"
                        }
                    ],
                    "intent_strength": "strong",
                    "show_intent": True
                },
                {
                    "id": "apollo_person_002", 
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "email": "jane.smith@healthcorp.com",
                    "email_status": "verified",
                    "title": "Vice President of Sales",
                    "linkedin_url": "https://linkedin.com/in/janesmith",
                    "headline": "VP Sales at HealthCorp | Healthcare Insurance Expert",
                    "organization": {
                        "id": "org_healthcorp",
                        "name": "HealthCorp Insurance",
                        "website_url": "https://healthcorp.com"
                    },
                    "intent_strength": "medium",
                    "show_intent": True
                }
            ],
            "pagination": {
                "page": 1,
                "per_page": 25,
                "total_entries": 47,
                "total_pages": 2
            },
            "breadcrumbs": [
                {
                    "label": "Companies",
                    "signal_field_name": "organization_locations",
                    "value": "United States",
                    "display_name": "United States"
                }
            ]
        }
    
    @staticmethod
    def apollo_people_search_empty():
        """Apollo.io empty search response."""
        return {
            "people": [],
            "pagination": {
                "page": 1,
                "per_page": 25,
                "total_entries": 0,
                "total_pages": 0
            },
            "breadcrumbs": []
        }
    
    @staticmethod
    def apollo_error_unauthorized():
        """Apollo.io unauthorized error response."""
        return {
            "error": "Unauthorized",
            "message": "Invalid API key provided"
        }
    
    @staticmethod
    def pipedrive_organization_create_success():
        """Pipedrive successful organization creation response."""
        return {
            "success": True,
            "data": {
                "id": 123,
                "company_id": 12345,
                "owner_id": {
                    "id": 1,
                    "name": "John Admin",
                    "email": "admin@company.com",
                    "has_pic": 1,
                    "pic_hash": "abcd1234",
                    "active_flag": True,
                    "value": 1
                },
                "name": "HealthCorp Insurance",
                "open_deals_count": 2,
                "related_open_deals_count": 2,
                "closed_deals_count": 5,
                "related_closed_deals_count": 5,
                "email_messages_count": 12,
                "people_count": 8,
                "activities_count": 15,
                "done_activities_count": 10,
                "undone_activities_count": 5,
                "files_count": 3,
                "notes_count": 7,
                "followers_count": 2,
                "won_deals_count": 4,
                "related_won_deals_count": 4,
                "lost_deals_count": 1,
                "related_lost_deals_count": 1,
                "active_flag": True,
                "category_id": None,
                "picture_id": None,
                "country_code": "US",
                "first_char": "H",
                "update_time": "2024-01-15 10:30:45",
                "add_time": "2024-01-15 10:30:45",
                "visible_to": "3",
                "next_activity_date": "2024-01-20",
                "next_activity_time": "14:00:00",
                "next_activity_id": 42,
                "last_activity_id": 38,
                "last_activity_date": "2024-01-10",
                "timeline_last_activity_time": "2024-01-10 16:30:00",
                "timeline_last_activity_time_by_owner": "2024-01-10 16:30:00",
                "address": "123 Healthcare Blvd, Medical City, CA 90210",
                "address_subpremise": "Suite 100",
                "address_street_number": "123",
                "address_route": "Healthcare Blvd",
                "address_sublocality": None,
                "address_locality": "Medical City",
                "address_admin_area_level_1": "CA",
                "address_admin_area_level_2": None,
                "address_country": "United States",
                "address_postal_code": "90210",
                "address_formatted_address": "123 Healthcare Blvd, Suite 100, Medical City, CA 90210, USA",
                "label": 4
            }
        }
    
    @staticmethod
    def pipedrive_organization_create_error():
        """Pipedrive organization creation error response."""
        return {
            "success": False,
            "error": "Name is required",
            "error_info": "The name field cannot be empty",
            "data": None,
            "additional_data": {
                "validation_errors": {
                    "name": ["This field is required"]
                }
            }
        }
    
    @staticmethod
    def pipedrive_organization_get_success():
        """Pipedrive successful organization retrieval response."""
        return {
            "success": True,
            "data": {
                "id": 123,
                "name": "HealthCorp Insurance",
                "people_count": 8,
                "owner_id": 1,
                "address": "123 Healthcare Blvd, Medical City, CA 90210",
                "active_flag": True,
                "cc_email": "healthcorp@deals.pipedrive.com",
                "value": 250000,
                "currency": "USD",
                "open_deals_count": 2,
                "closed_deals_count": 5,
                "won_deals_count": 4,
                "lost_deals_count": 1,
                "activities_count": 15,
                "done_activities_count": 10,
                "undone_activities_count": 5
            }
        }
    
    @staticmethod
    def proxycurl_company_employees_success():
        """Proxycurl successful company employees response."""
        return {
            "employees": [
                {
                    "profile_url": "https://linkedin.com/in/johndoe-ceo",
                    "profile": {
                        "public_identifier": "johndoe-ceo",
                        "profile_pic_url": "https://media.licdn.com/dms/image/profile-pic.jpg",
                        "background_cover_image_url": None,
                        "first_name": "John",
                        "last_name": "Doe",
                        "full_name": "John Doe",
                        "follower_count": 1523,
                        "occupation": "Chief Executive Officer at HealthCorp Insurance",
                        "headline": "CEO at HealthCorp Insurance | Transforming Healthcare Coverage",
                        "summary": "Experienced healthcare executive with over 15 years of leadership in insurance and healthcare technology. Passionate about making healthcare more accessible and affordable for everyone.",
                        "country": "United States",
                        "country_full_name": "United States of America",
                        "city": "San Francisco",
                        "state": "California",
                        "experiences": [
                            {
                                "starts_at": {"day": 1, "month": 1, "year": 2020},
                                "ends_at": None,
                                "company": "HealthCorp Insurance",
                                "company_linkedin_profile_url": "https://linkedin.com/company/healthcorp",
                                "title": "Chief Executive Officer",
                                "description": "Leading the company's strategic vision and digital transformation initiatives. Overseeing operations across 12 states with focus on expanding coverage options.",
                                "location": "San Francisco, California",
                                "logo_url": "https://healthcorp.com/logo.png"
                            },
                            {
                                "starts_at": {"day": 1, "month": 6, "year": 2017},
                                "ends_at": {"day": 31, "month": 12, "year": 2019},
                                "company": "MedTech Solutions",
                                "title": "VP of Operations",
                                "description": "Managed operations for healthcare technology platform serving 500+ healthcare providers.",
                                "location": "San Francisco, California"
                            }
                        ],
                        "education": [
                            {
                                "starts_at": {"day": 1, "month": 9, "year": 1998},
                                "ends_at": {"day": 31, "month": 5, "year": 2002},
                                "field_of_study": "Business Administration",
                                "degree_name": "Master of Business Administration (MBA)",
                                "school": "Stanford Graduate School of Business",
                                "school_linkedin_profile_url": "https://linkedin.com/school/stanford-gsb",
                                "description": "Concentration in Healthcare Management and Strategy"
                            }
                        ],
                        "languages": ["English", "Spanish"],
                        "accomplishment_organisations": [],
                        "accomplishment_publications": [],
                        "accomplishment_honors_awards": [],
                        "accomplishment_patents": [],
                        "accomplishment_courses": [],
                        "accomplishment_projects": [],
                        "accomplishment_test_scores": [],
                        "volunteer_work": [],
                        "certifications": [],
                        "connections": 500,
                        "people_also_viewed": [],
                        "recommendations": ["John is an exceptional leader...", "Outstanding strategic vision..."],
                        "activities": [],
                        "similarly_named_profiles": [],
                        "articles": [],
                        "groups": []
                    }
                },
                {
                    "profile_url": "https://linkedin.com/in/janesmith-vpsales",
                    "profile": {
                        "public_identifier": "janesmith-vpsales",
                        "first_name": "Jane",
                        "last_name": "Smith",
                        "full_name": "Jane Smith",
                        "headline": "VP Sales at HealthCorp Insurance | Healthcare Insurance Expert",
                        "summary": "Sales leader with 12+ years in healthcare insurance. Expert in enterprise sales and client relationship management.",
                        "country": "United States",
                        "city": "Los Angeles",
                        "state": "California",
                        "experiences": [
                            {
                                "starts_at": {"day": 15, "month": 3, "year": 2021},
                                "ends_at": None,
                                "company": "HealthCorp Insurance",
                                "title": "Vice President of Sales",
                                "description": "Leading national sales team of 25+ representatives. Responsible for $50M+ annual revenue target.",
                                "location": "Los Angeles, California"
                            }
                        ],
                        "connections": 1250
                    }
                }
            ],
            "next_page": None,
            "total_result_count": 47
        }
    
    @staticmethod
    def proxycurl_company_profile_success():
        """Proxycurl successful company profile response."""
        return {
            "linkedin_internal_id": "1234567",
            "description": "HealthCorp Insurance is a leading provider of comprehensive health insurance solutions, serving individuals, families, and businesses across multiple states. We are committed to making healthcare more accessible and affordable through innovative coverage options and exceptional customer service.",
            "website": "https://healthcorp.com",
            "industry": "Insurance",
            "company_size": [201, 500],
            "company_size_on_linkedin": 347,
            "hq": {
                "country": "United States",
                "city": "San Francisco",
                "postal_code": "94105",
                "line_1": "123 Healthcare Boulevard",
                "is_hq": True
            },
            "company_type": "PRIVATELY_HELD",
            "founded_year": 2015,
            "specialities": [
                "Health Insurance",
                "Medical Coverage",
                "Employee Benefits",
                "Individual Plans",
                "Family Coverage",
                "Healthcare Technology",
                "Claims Processing",
                "Provider Networks"
            ],
            "locations": [
                {
                    "country": "United States",
                    "city": "San Francisco",
                    "postal_code": "94105",
                    "line_1": "123 Healthcare Boulevard",
                    "is_hq": True
                },
                {
                    "country": "United States",
                    "city": "Los Angeles",
                    "postal_code": "90210",
                    "line_1": "456 Insurance Way",
                    "is_hq": False
                },
                {
                    "country": "United States",
                    "city": "Austin",
                    "postal_code": "78701",
                    "line_1": "789 Health Plaza",
                    "is_hq": False
                }
            ],
            "name": "HealthCorp Insurance",
            "tagline": "Making Healthcare Accessible for Everyone",
            "universal_name_id": "healthcorp-insurance",
            "profile_pic_url": "https://media.licdn.com/dms/image/company-logo.png",
            "background_cover_image_url": "https://media.licdn.com/dms/image/company-cover.jpg",
            "search_id": "1234567",
            "similar_companies": [
                {
                    "name": "BlueCross BlueShield",
                    "link": "https://linkedin.com/company/bluecross-blueshield",
                    "industry": "Insurance",
                    "location": "Chicago, Illinois"
                },
                {
                    "name": "Aetna",
                    "link": "https://linkedin.com/company/aetna",
                    "industry": "Insurance", 
                    "location": "Hartford, Connecticut"
                }
            ],
            "affiliated_companies": [],
            "updates": [
                {
                    "article_link": "https://healthcorp.com/news/expansion",
                    "image": "https://healthcorp.com/images/news1.jpg",
                    "posted_on": "2024-01-10",
                    "text": "Excited to announce our expansion into two new states, bringing quality healthcare coverage to even more families!"
                }
            ],
            "follower_count": 15420
        }
    
    @staticmethod
    def proxycurl_error_rate_limited():
        """Proxycurl rate limit error response."""
        return {
            "error": "Rate limit exceeded",
            "detail": "You have exceeded your rate limit. Please try again later.",
            "retry_after": 60
        }
    
    @staticmethod
    def proxycurl_error_insufficient_credits():
        """Proxycurl insufficient credits error response."""
        return {
            "error": "Insufficient credits",
            "detail": "Your account does not have enough credits to perform this request. Please add more credits.",
            "credits_remaining": 0
        }


class MockDatabaseResponses:
    """Mock database response fixtures."""
    
    @staticmethod
    def company_with_contacts():
        """Mock company with associated contacts."""
        from unittest.mock import Mock
        
        company = Mock()
        company.id = str(uuid4())
        company.name = "HealthCorp Insurance"
        company.naics_code = "621111"
        company.employee_count_min = 200
        company.employee_count_max = 500
        company.state = "CA"
        company.city = "San Francisco"
        company.website = "https://healthcorp.com"
        company.lead_score = 85
        
        # Mock contacts
        contacts = []
        for i in range(3):
            contact = Mock()
            contact.id = str(uuid4())
            contact.first_name = f"Contact{i}"
            contact.last_name = f"Person{i}"
            contact.email = f"contact{i}@healthcorp.com"
            contact.title = ["CEO", "VP Sales", "Director"][i]
            contact.company_id = company.id
            contacts.append(contact)
        
        company.contacts = contacts
        return company
    
    @staticmethod
    def company_without_contacts():
        """Mock company without contacts."""
        from unittest.mock import Mock
        
        company = Mock()
        company.id = str(uuid4())
        company.name = "MedCare Solutions"
        company.naics_code = "621210"
        company.employee_count_min = 50
        company.employee_count_max = 100
        company.state = "TX"
        company.city = "Austin"
        company.website = "https://medcare.com"
        company.lead_score = None
        company.contacts = []
        
        return company
    
    @staticmethod
    def lead_score_high_quality():
        """Mock high-quality lead score."""
        from unittest.mock import Mock
        from models.lead_score import LeadScore
        
        lead_score = Mock(spec=LeadScore)
        lead_score.id = str(uuid4())
        lead_score.company_id = str(uuid4())
        lead_score.total_score = 88
        lead_score.score_grade = "A-"
        lead_score.industry_score = 85
        lead_score.size_score = 90
        lead_score.location_score = 88
        lead_score.data_quality_score = 89
        lead_score.engagement_score = 82
        lead_score.industry_risk_level = "low"
        lead_score.size_category = "medium"
        lead_score.scoring_factors = {
            "naics_match": True,
            "employee_range_fit": True,
            "geographic_preference": True,
            "data_completeness": 0.95
        }
        lead_score.score_reasons = [
            "Strong industry fit",
            "Optimal company size",
            "High data quality",
            "Good geographic location"
        ]
        lead_score.recommendations = "Prioritize for immediate outreach. Focus on C-level executives."
        lead_score.created_at = datetime.utcnow()
        
        return lead_score


class MockQueueMessages:
    """Mock message queue payloads."""
    
    @staticmethod
    def enrichment_message():
        """Standard enrichment queue message."""
        return {
            "company_id": str(uuid4()),
            "priority": "normal",
            "source": "scraper",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def scoring_message():
        """Standard scoring queue message."""
        return {
            "company_id": str(uuid4()),
            "trigger": "enrichment_completed",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def crm_sync_message():
        """Standard CRM sync queue message."""
        return {
            "company_id": str(uuid4()),
            "score": 87,
            "priority": "high",
            "timestamp": datetime.utcnow().isoformat()
        }


class MockScrapingResults:
    """Mock scraping operation results."""
    
    @staticmethod
    def bls_scraper_success():
        """Successful BLS scraper result."""
        return {
            "success": True,
            "stats": {
                "records_processed": 1250,
                "records_created": 950,
                "records_updated": 300,
                "errors": 0,
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T11:30:00Z",
                "duration_seconds": 5400
            },
            "metadata": {
                "states_scraped": ["CA", "TX", "NY"],
                "naics_codes": ["621111", "621210", "621310"],
                "data_source": "BLS QCEW"
            }
        }
    
    @staticmethod
    def bls_scraper_partial_failure():
        """Partial failure BLS scraper result."""
        return {
            "success": True,
            "stats": {
                "records_processed": 800,
                "records_created": 600,
                "records_updated": 150,
                "errors": 50,
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T10:45:00Z",
                "duration_seconds": 2700
            },
            "warnings": [
                "Failed to process some records due to data quality issues",
                "Network timeouts encountered for some requests"
            ],
            "error_details": {
                "network_errors": 25,
                "data_validation_errors": 15,
                "parsing_errors": 10
            }
        }
    
    @staticmethod
    def scraper_complete_failure():
        """Complete scraper failure result."""
        return {
            "success": False,
            "error": "Database connection failed",
            "error_type": "DatabaseError",
            "stats": {
                "records_processed": 0,
                "records_created": 0,
                "records_updated": 0,
                "errors": 1,
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T10:01:00Z",
                "duration_seconds": 60
            },
            "error_details": {
                "database_errors": 1,
                "network_errors": 0,
                "parsing_errors": 0
            }
        }