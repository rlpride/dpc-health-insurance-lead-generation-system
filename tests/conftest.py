"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime
from uuid import uuid4

from tests.fixtures.api_responses import (
    MockAPIResponses, 
    MockDatabaseResponses, 
    MockQueueMessages,
    MockScrapingResults
)


# Configure asyncio for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Database fixtures
@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    with patch('models.get_db_session') as mock_session:
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_session.return_value.__exit__.return_value = None
        yield mock_db


@pytest.fixture
def sample_company():
    """Sample company fixture for testing."""
    return MockDatabaseResponses.company_with_contacts()


@pytest.fixture
def sample_company_no_contacts():
    """Sample company without contacts fixture."""
    return MockDatabaseResponses.company_without_contacts()


@pytest.fixture
def sample_lead_score():
    """Sample lead score fixture."""
    return MockDatabaseResponses.lead_score_high_quality()


# API Response fixtures
@pytest.fixture
def apollo_success_response():
    """Apollo API success response fixture."""
    return MockAPIResponses.apollo_people_search_success()


@pytest.fixture
def apollo_empty_response():
    """Apollo API empty response fixture."""
    return MockAPIResponses.apollo_people_search_empty()


@pytest.fixture
def pipedrive_success_response():
    """Pipedrive API success response fixture."""
    return MockAPIResponses.pipedrive_organization_create_success()


@pytest.fixture
def proxycurl_success_response():
    """Proxycurl API success response fixture."""
    return MockAPIResponses.proxycurl_company_employees_success()


# Queue message fixtures
@pytest.fixture
def enrichment_message():
    """Enrichment queue message fixture."""
    return MockQueueMessages.enrichment_message()


@pytest.fixture
def scoring_message():
    """Scoring queue message fixture."""
    return MockQueueMessages.scoring_message()


@pytest.fixture
def crm_sync_message():
    """CRM sync queue message fixture."""
    return MockQueueMessages.crm_sync_message()


# Scraping result fixtures
@pytest.fixture
def bls_scraper_success():
    """BLS scraper success result fixture."""
    return MockScrapingResults.bls_scraper_success()


@pytest.fixture
def bls_scraper_failure():
    """BLS scraper failure result fixture."""
    return MockScrapingResults.scraper_complete_failure()


# Environment fixtures
@pytest.fixture
def test_env_vars():
    """Test environment variables."""
    return {
        "APOLLO_API_KEY": "test-apollo-key",
        "PIPEDRIVE_API_KEY": "test-pipedrive-key", 
        "PIPEDRIVE_DOMAIN": "test-domain",
        "PROXYCURL_API_KEY": "test-proxycurl-key",
        "DATABASE_URL": "postgresql://test:test@localhost/test_db",
        "REDIS_URL": "redis://localhost:6379/1",
        "RABBITMQ_URL": "amqp://test:test@localhost:5672/test_vhost"
    }


@pytest.fixture
def temp_directory():
    """Temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = Mock()
    settings.high_score_threshold = 80
    settings.medium_score_threshold = 60
    settings.apollo_api_key = "test-apollo-key"
    settings.pipedrive_api_key = "test-pipedrive-key"
    settings.pipedrive_domain = "test-domain"
    settings.proxycurl_api_key = "test-proxycurl-key"
    settings.database_url = "postgresql://test:test@localhost/test_db"
    settings.redis_url = "redis://localhost:6379/1"
    settings.rabbitmq_url = "amqp://test:test@localhost:5672/test_vhost"
    return settings


# Worker fixtures
@pytest.fixture
def mock_enrichment_worker():
    """Mock enrichment worker for testing."""
    from workers.enrichment_worker import EnrichmentWorker
    
    with patch.object(EnrichmentWorker, '__init__', return_value=None):
        worker = EnrichmentWorker.__new__(EnrichmentWorker)
        worker.worker_id = "test-enrichment-worker"
        worker.settings = Mock()
        worker.settings.apollo_api_key = "test-apollo-key"
        worker.settings.proxycurl_api_key = "test-proxycurl-key"
        
        # Mock methods
        worker.enrich_with_apollo = Mock()
        worker.enrich_with_proxycurl = Mock()
        worker.publish_message = Mock()
        
        yield worker


@pytest.fixture
def mock_scoring_worker():
    """Mock scoring worker for testing."""
    from workers.scoring_worker import ScoringWorker
    
    with patch.object(ScoringWorker, '__init__', return_value=None):
        worker = ScoringWorker.__new__(ScoringWorker)
        worker.worker_id = "test-scoring-worker"
        worker.settings = Mock()
        worker.settings.high_score_threshold = 80
        
        # Mock methods
        worker.calculate_score = Mock()
        worker.publish_message = Mock()
        
        yield worker


@pytest.fixture
def mock_crm_sync_worker():
    """Mock CRM sync worker for testing."""
    from workers.crm_sync_worker import CrmSyncWorker
    
    with patch.object(CrmSyncWorker, '__init__', return_value=None):
        worker = CrmSyncWorker.__new__(CrmSyncWorker)
        worker.worker_id = "test-crm-sync-worker"
        worker.settings = Mock()
        worker.settings.pipedrive_api_key = "test-pipedrive-key"
        worker.settings.pipedrive_domain = "test-domain"
        
        # Mock methods
        worker.sync_to_pipedrive = Mock()
        worker.publish_message = Mock()
        
        yield worker


# API Client fixtures
@pytest.fixture
def mock_apollo_client():
    """Mock Apollo API client."""
    from api.apollo.client import ApolloClient
    
    with patch.object(ApolloClient, '__init__', return_value=None):
        client = ApolloClient.__new__(ApolloClient)
        client.api_key = "test-apollo-key"
        client.headers = {"Content-Type": "application/json"}
        
        # Mock methods
        client.search_people = Mock()
        
        yield client


@pytest.fixture 
def mock_pipedrive_client():
    """Mock Pipedrive API client."""
    from api.pipedrive.client import PipedriveClient
    
    with patch.object(PipedriveClient, '__init__', return_value=None):
        client = PipedriveClient.__new__(PipedriveClient)
        client.api_key = "test-pipedrive-key"
        client.domain = "test-domain"
        client.base_url = "https://test-domain.pipedrive.com/api/v1"
        
        # Mock methods
        client.create_organization = Mock()
        client.get_organization = Mock()
        
        yield client


@pytest.fixture
def mock_proxycurl_client():
    """Mock Proxycurl API client."""
    from api.proxycurl.client import ProxycurlClient
    
    with patch.object(ProxycurlClient, '__init__', return_value=None):
        client = ProxycurlClient.__new__(ProxycurlClient)
        client.api_key = "test-proxycurl-key"
        client.headers = {"Authorization": "Bearer test-proxycurl-key"}
        
        # Mock methods
        client.get_company_employees = Mock()
        client.get_company_profile = Mock()
        
        yield client


# Test data generators
@pytest.fixture
def generate_companies():
    """Generator for creating test companies."""
    def _generate(count=10, **kwargs):
        companies = []
        for i in range(count):
            company = Mock()
            company.id = str(uuid4())
            company.name = kwargs.get('name', f"Test Company {i}")
            company.naics_code = kwargs.get('naics_code', "621111")
            company.employee_count_min = kwargs.get('employee_count_min', 50 + i)
            company.employee_count_max = kwargs.get('employee_count_max', 100 + i)
            company.state = kwargs.get('state', ["CA", "TX", "NY"][i % 3])
            company.city = kwargs.get('city', f"City {i}")
            company.website = kwargs.get('website', f"https://company{i}.com")
            company.contacts = kwargs.get('contacts', [])
            company.lead_score = kwargs.get('lead_score', None)
            companies.append(company)
        return companies
    return _generate


@pytest.fixture
def generate_contacts():
    """Generator for creating test contacts."""
    def _generate(count=5, company_id=None, **kwargs):
        contacts = []
        for i in range(count):
            contact = Mock()
            contact.id = str(uuid4())
            contact.company_id = company_id or str(uuid4())
            contact.first_name = kwargs.get('first_name', f"First{i}")
            contact.last_name = kwargs.get('last_name', f"Last{i}")
            contact.email = kwargs.get('email', f"contact{i}@company.com")
            contact.title = kwargs.get('title', ["CEO", "VP", "Director", "Manager", "Executive"][i % 5])
            contact.linkedin_url = kwargs.get('linkedin_url', f"https://linkedin.com/in/contact{i}")
            contacts.append(contact)
        return contacts
    return _generate


# Performance test fixtures
@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.duration = None
        
        def __enter__(self):
            self.start_time = time.perf_counter()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.end_time = time.perf_counter()
            self.duration = self.end_time - self.start_time
    
    return Timer


@pytest.fixture
def memory_profiler():
    """Memory profiler for performance testing."""
    import psutil
    import gc
    
    class MemoryProfiler:
        def __init__(self):
            self.process = psutil.Process()
            self.initial_memory = None
            self.final_memory = None
        
        def __enter__(self):
            self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            gc.collect()
        
        @property
        def memory_increase(self):
            if self.final_memory and self.initial_memory:
                return self.final_memory - self.initial_memory
            return 0
    
    return MemoryProfiler


# Pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Auto-use fixtures for common setup
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, test_env_vars):
    """Automatically set up test environment for all tests."""
    # Set test environment variables
    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)
    
    # Mock external dependencies that should never be called in tests
    with patch('redis.Redis'), \
         patch('pika.BlockingConnection'), \
         patch('sqlalchemy.create_engine'):
        yield


@pytest.fixture(autouse=True)
def isolate_tests():
    """Ensure test isolation by clearing any global state."""
    # Clear any cached modules or global state
    yield
    # Cleanup after test
    import gc
    gc.collect()


# Test collection customization
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file structure."""
    for item in items:
        # Add markers based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "end_to_end" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)


# Test reporting
@pytest.fixture(scope="session", autouse=True)
def test_report_setup():
    """Set up test reporting."""
    print("\n" + "="*80)
    print("DPC Health Insurance Lead Generation System - Test Suite")
    print("="*80)
    yield
    print("\n" + "="*80)
    print("Test Suite Completed")
    print("="*80)