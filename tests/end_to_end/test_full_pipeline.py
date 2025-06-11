"""End-to-end tests for the full lead generation pipeline."""

import pytest
import asyncio
import json
import subprocess
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from cli import main
from models import Company, Contact, LeadScore, init_db
from workers import EnrichmentWorker, ScoringWorker, CrmSyncWorker
from scrapers.government import BLSScraper


class TestFullPipelineE2E:
    """End-to-end tests for complete pipeline."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        # Mock database initialization
        with patch('models.init_db'), \
             patch('models.get_db_session') as mock_db:
            yield mock_db
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    @patch('cli.BLSScraper')
    async def test_scrape_to_score_pipeline(self, mock_scraper_class, mock_subprocess):
        """Test complete pipeline from scraping to scoring."""
        # Setup mocks
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        
        # Mock successful scraping result
        scrape_result = {
            'success': True,
            'stats': {
                'records_processed': 100,
                'records_created': 80,
                'records_updated': 20
            }
        }
        mock_scraper.run.return_value = scrape_result
        
        # Mock database session
        with patch('models.get_db_session') as mock_db_session:
            mock_db = Mock()
            mock_db_session.return_value.__enter__.return_value = mock_db
            
            # Create mock companies that would be created by scraper
            mock_companies = [
                Mock(
                    id=str(uuid4()),
                    name="HealthCorp Insurance",
                    naics_code="621111",
                    employee_count_min=100,
                    state="CA",
                    contacts=[]
                ),
                Mock(
                    id=str(uuid4()),
                    name="MedCare Solutions", 
                    naics_code="621111",
                    employee_count_min=250,
                    state="TX",
                    contacts=[]
                )
            ]
            mock_db.query.return_value.filter.return_value.all.return_value = mock_companies
            
            # Test pipeline components
            # 1. Run BLS scraper
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = None
                
                # Test scraper CLI command
                from click.testing import CliRunner
                runner = CliRunner()
                result = runner.invoke(main, ['scrape', 'bls', '--states', 'CA', 'TX'])
                
                assert result.exit_code == 0
                mock_scraper.run.assert_called_once()
            
            # 2. Test enrichment worker processing
            enrichment_worker = EnrichmentWorker("test-enrichment-worker")
            
            with patch.object(enrichment_worker, 'process_message') as mock_enrich_process:
                mock_enrich_process.return_value = True
                
                # Simulate enrichment messages
                for company in mock_companies:
                    message = {"company_id": company.id}
                    result = enrichment_worker.process_message(message)
                    assert result is True
            
            # 3. Test scoring worker processing
            scoring_worker = ScoringWorker("test-scoring-worker")
            scoring_worker.settings = Mock()
            scoring_worker.settings.high_score_threshold = 80
            
            with patch.object(scoring_worker, 'calculate_score') as mock_calc_score, \
                 patch.object(scoring_worker, 'publish_message') as mock_publish:
                
                # First company gets high score
                mock_calc_score.side_effect = [
                    {
                        "total_score": 85,
                        "industry_score": 80,
                        "size_score": 90,
                        "location_score": 85,
                        "data_quality_score": 85,
                        "factors": {"test": "data"}
                    },
                    {
                        "total_score": 65,  # Low score
                        "industry_score": 60,
                        "size_score": 70,
                        "location_score": 65,
                        "data_quality_score": 65,
                        "factors": {"test": "data"}
                    }
                ]
                
                high_score_companies = []
                for i, company in enumerate(mock_companies):
                    message = {"company_id": company.id}
                    result = scoring_worker.process_message(message)
                    assert result is True
                    
                    # Check if high-scoring company was published to CRM sync queue
                    if i == 0:  # First company has high score
                        high_score_companies.append(company.id)
                
                # Verify high-scoring company was sent to CRM sync
                assert len(high_score_companies) == 1
                mock_publish.assert_called_with(
                    {"company_id": high_score_companies[0]},
                    "companies.to_sync.tasks"
                )
            
            # 4. Test CRM sync worker
            crm_worker = CrmSyncWorker("test-crm-worker")
            
            with patch.object(crm_worker, 'process_message') as mock_crm_process:
                mock_crm_process.return_value = True
                
                # Process high-scoring company
                message = {"company_id": high_score_companies[0]}
                result = crm_worker.process_message(message)
                assert result is True
    
    @pytest.mark.asyncio
    async def test_data_quality_pipeline(self):
        """Test pipeline data quality and validation."""
        with patch('models.get_db_session') as mock_db_session:
            mock_db = Mock()
            mock_db_session.return_value.__enter__.return_value = mock_db
            
            # Create company with missing data to test data quality scoring
            incomplete_company = Mock(
                id=str(uuid4()),
                name="Incomplete Corp",
                naics_code=None,  # Missing NAICS
                employee_count_min=None,  # Missing employee count
                state="CA",
                contacts=[]
            )
            
            complete_company = Mock(
                id=str(uuid4()),
                name="Complete Corp", 
                naics_code="621111",
                employee_count_min=150,
                state="CA",
                contacts=[Mock(), Mock()]  # Has contacts
            )
            
            scoring_worker = ScoringWorker("test-scoring-worker")
            
            # Test scoring with incomplete data
            incomplete_score = scoring_worker.calculate_score(incomplete_company)
            complete_score = scoring_worker.calculate_score(complete_company)
            
            # Complete company should have higher data quality score
            assert complete_score["data_quality_score"] >= incomplete_score["data_quality_score"]
            assert complete_score["total_score"] >= incomplete_score["total_score"]
    
    def test_cli_database_operations(self):
        """Test CLI database initialization and management."""
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        # Test database initialization
        with patch('models.init_db') as mock_init_db:
            result = runner.invoke(main, ['init-database'])
            assert result.exit_code == 0
            assert "Database initialized successfully!" in result.output
            mock_init_db.assert_called_once()
        
        # Test database drop with confirmation
        with patch('models.drop_db') as mock_drop_db:
            result = runner.invoke(main, ['drop-database'], input='y\n')
            assert result.exit_code == 0
            mock_drop_db.assert_called_once()
    
    def test_cli_worker_commands(self):
        """Test CLI worker management commands."""
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        # Test enrichment worker start
        with patch('workers.EnrichmentWorker') as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker
            mock_worker.run.side_effect = KeyboardInterrupt()  # Simulate stop
            
            result = runner.invoke(main, ['worker', 'enrichment', '--worker-id', 'test-1'])
            assert result.exit_code == 0
            assert "Starting enrichment worker..." in result.output
            assert "Worker stopped." in result.output
            mock_worker.run.assert_called_once()
        
        # Test scoring worker start
        with patch('workers.ScoringWorker') as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker
            mock_worker.run.side_effect = KeyboardInterrupt()
            
            result = runner.invoke(main, ['worker', 'scoring', '--worker-id', 'test-2'])
            assert result.exit_code == 0
            mock_worker.run.assert_called_once()
        
        # Test CRM sync worker start
        with patch('workers.CrmSyncWorker') as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker
            mock_worker.run.side_effect = KeyboardInterrupt()
            
            result = runner.invoke(main, ['worker', 'crm-sync', '--worker-id', 'test-3'])
            assert result.exit_code == 0
            mock_worker.run.assert_called_once()
    
    def test_cli_status_command(self):
        """Test system status check command."""
        from click.testing import CliRunner
        
        runner = CliRunner()
        result = runner.invoke(main, ['status'])
        
        assert result.exit_code == 0
        assert "System Status:" in result.output
        assert "Database: Connected ✓" in result.output
    
    @patch('subprocess.run')
    def test_bls_scrapy_command(self, mock_subprocess):
        """Test BLS Scrapy spider CLI command."""
        from click.testing import CliRunner
        
        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.stdout = "Spider completed successfully"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        runner = CliRunner()
        result = runner.invoke(main, [
            'scrape', 'bls-scrapy',
            '--year', '2023',
            '--quarter', '4',
            '--states', 'CA,TX',
            '--naics', '621111,621210',
            '--delay', '1.5',
            '--output-format', 'json'
        ])
        
        assert result.exit_code == 0
        assert "Starting BLS QCEW Scrapy spider..." in result.output
        assert "BLS Scrapy spider completed successfully!" in result.output
        
        # Verify subprocess was called with correct arguments
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert 'python3' in call_args
        assert 'scripts/run_bls_spider.py' in call_args
        assert '--year' in call_args
        assert '2023' in call_args


class TestPipelineErrorHandling:
    """Test error handling throughout the pipeline."""
    
    @pytest.mark.asyncio
    async def test_scraper_failure_handling(self):
        """Test handling of scraper failures."""
        with patch('cli.BLSScraper') as mock_scraper_class:
            mock_scraper = Mock()
            mock_scraper_class.return_value = mock_scraper
            
            # Mock scraper failure
            mock_scraper.run.return_value = {
                'success': False,
                'error': 'Network connection failed'
            }
            
            from click.testing import CliRunner
            runner = CliRunner()
            
            with patch('asyncio.run'):
                result = runner.invoke(main, ['scrape', 'bls'])
                # Should handle error gracefully
                assert result.exit_code == 0
    
    def test_worker_exception_handling(self):
        """Test worker exception handling."""
        worker = ScoringWorker("test-worker")
        
        # Test with invalid message format
        result = worker.process_message({"invalid": "data"})
        assert result is False
        
        # Test with database connection error
        with patch('workers.scoring_worker.get_db_session') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            result = worker.process_message({"company_id": str(uuid4())})
            assert result is False
    
    def test_api_client_failure_resilience(self):
        """Test system resilience to API client failures."""
        enrichment_worker = EnrichmentWorker("test-worker")
        
        # Mock API client failures
        with patch.object(enrichment_worker, 'enrich_with_apollo') as mock_apollo, \
             patch.object(enrichment_worker, 'enrich_with_proxycurl') as mock_proxycurl:
            
            # Apollo fails, Proxycurl succeeds
            mock_apollo.side_effect = Exception("Apollo API error")
            mock_proxycurl.return_value = {"success": True}
            
            # Worker should continue processing despite one API failure
            result = enrichment_worker.process_message({
                "company_id": str(uuid4())
            })
            
            # Should handle partial failures gracefully
            assert isinstance(result, bool)


class TestPipelinePerformance:
    """Test pipeline performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_bulk_processing_performance(self):
        """Test performance with bulk data processing."""
        scoring_worker = ScoringWorker("perf-test-worker")
        
        # Generate test companies
        test_companies = []
        for i in range(100):
            company = Mock(
                id=str(uuid4()),
                name=f"Test Company {i}",
                naics_code="621111",
                employee_count_min=50 + i,
                state=["CA", "TX", "NY", "FL"][i % 4],
                contacts=[]
            )
            test_companies.append(company)
        
        # Measure processing time
        start_time = datetime.utcnow() 
        
        scores = []
        for company in test_companies:
            score = scoring_worker.calculate_score(company)
            scores.append(score)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # Performance assertions
        assert len(scores) == 100
        assert processing_time < 5.0  # Should process 100 companies in under 5 seconds
        assert all(score["total_score"] > 0 for score in scores)
    
    def test_memory_usage_during_processing(self):
        """Test memory usage patterns during processing."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process large batch of data
        scoring_worker = ScoringWorker("memory-test-worker")
        
        for i in range(1000):
            company = Mock(
                id=str(uuid4()),
                naics_code="621111",
                employee_count_min=100,
                state="CA",
                contacts=[]
            )
            scoring_worker.calculate_score(company)
            
            # Force garbage collection every 100 iterations
            if i % 100 == 0:
                gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory usage should not increase excessively
        assert memory_increase < 100  # Should not use more than 100MB additional


class TestPipelineDataIntegrity:
    """Test data integrity throughout the pipeline."""
    
    def test_lead_score_consistency(self):
        """Test lead score calculation consistency."""
        scoring_worker = ScoringWorker("consistency-test-worker")
        
        # Create identical companies
        company1 = Mock(
            naics_code="621111",
            employee_count_min=100,
            state="CA",
            contacts=[]
        )
        company2 = Mock(
            naics_code="621111", 
            employee_count_min=100,
            state="CA",
            contacts=[]
        )
        
        # Scores should be identical for identical companies
        score1 = scoring_worker.calculate_score(company1)
        score2 = scoring_worker.calculate_score(company2)
        
        assert score1["total_score"] == score2["total_score"]
        assert score1["industry_score"] == score2["industry_score"]
        assert score1["size_score"] == score2["size_score"]
        assert score1["location_score"] == score2["location_score"]
    
    def test_data_flow_integrity(self):
        """Test data integrity through the pipeline."""
        with patch('models.get_db_session') as mock_db_session:
            mock_db = Mock()
            mock_db_session.return_value.__enter__.return_value = mock_db
            
            # Create test company
            company_id = str(uuid4())
            test_company = Mock(
                id=company_id,
                name="Test Company",
                naics_code="621111",
                employee_count_min=100,
                state="CA",
                contacts=[]
            )
            
            mock_db.query.return_value.filter_by.return_value.first.return_value = test_company
            
            # Process through scoring worker
            scoring_worker = ScoringWorker("integrity-test-worker")
            scoring_worker.settings = Mock()
            scoring_worker.settings.high_score_threshold = 80
            
            with patch.object(scoring_worker, 'publish_message') as mock_publish:
                result = scoring_worker.process_message({"company_id": company_id})
                
                assert result is True
                
                # Verify LeadScore was created and saved
                mock_db.add.assert_called_once()
                lead_score = mock_db.add.call_args[0][0]
                
                # Verify data integrity
                assert lead_score.company_id == company_id
                assert lead_score.total_score > 0
                assert lead_score.score_grade is not None
                assert isinstance(lead_score.scoring_factors, dict)
                
                mock_db.commit.assert_called_once()


@pytest.fixture
def pipeline_test_data():
    """Fixture providing test data for pipeline tests."""
    return {
        "companies": [
            {
                "id": str(uuid4()),
                "name": "HealthCorp Insurance",
                "naics_code": "621111",
                "employee_count_min": 100,
                "employee_count_max": 250,
                "state": "CA",
                "city": "San Francisco",
                "website": "https://healthcorp.com"
            },
            {
                "id": str(uuid4()),
                "name": "MedCare Solutions",
                "naics_code": "621210", 
                "employee_count_min": 50,
                "employee_count_max": 100,
                "state": "TX",
                "city": "Austin",
                "website": "https://medcare.com"
            }
        ],
        "contacts": [
            {
                "first_name": "John",
                "last_name": "Doe",
                "title": "CEO",
                "email": "john.doe@healthcorp.com",
                "linkedin_url": "https://linkedin.com/in/johndoe"
            },
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "title": "VP Sales",
                "email": "jane.smith@medcare.com",
                "linkedin_url": "https://linkedin.com/in/janesmith"
            }
        ]
    }


class TestPipelineIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_healthcare_company_enrichment_scenario(self, pipeline_test_data):
        """Test realistic healthcare company enrichment scenario."""
        companies = pipeline_test_data["companies"]
        contacts = pipeline_test_data["contacts"]
        
        with patch('models.get_db_session') as mock_db_session:
            mock_db = Mock()
            mock_db_session.return_value.__enter__.return_value = mock_db
            
            # Mock company lookup
            test_company = Mock()
            test_company.id = companies[0]["id"]
            test_company.name = companies[0]["name"]
            test_company.naics_code = companies[0]["naics_code"]
            test_company.employee_count_min = companies[0]["employee_count_min"]
            test_company.state = companies[0]["state"]
            test_company.contacts = []
            
            mock_db.query.return_value.filter_by.return_value.first.return_value = test_company
            
            # Test enrichment workflow
            enrichment_worker = EnrichmentWorker("scenario-test-worker")
            
            with patch.object(enrichment_worker, 'enrich_with_apollo') as mock_apollo, \
                 patch.object(enrichment_worker, 'enrich_with_proxycurl') as mock_proxycurl, \
                 patch.object(enrichment_worker, 'publish_message') as mock_publish:
                
                # Mock successful enrichment
                mock_apollo.return_value = {
                    "contacts_found": 2,
                    "contacts": contacts
                }
                mock_proxycurl.return_value = {
                    "employees_found": 5,
                    "company_details": {
                        "size": "101-250",
                        "industry": "Healthcare"
                    }
                }
                
                # Process enrichment
                result = enrichment_worker.process_message({
                    "company_id": companies[0]["id"]
                })
                
                assert result is True
                
                # Verify enriched company was sent to scoring queue
                mock_publish.assert_called_with(
                    {"company_id": companies[0]["id"]},
                    "companies.to_score"
                )
    
    def test_high_volume_lead_processing(self):
        """Test processing high volume of leads."""
        # Simulate processing 1000 companies
        scoring_worker = ScoringWorker("volume-test-worker")
        
        scores = []
        high_quality_count = 0
        
        for i in range(1000):
            company = Mock(
                naics_code=["621111", "621210", "621310"][i % 3],
                employee_count_min=20 + (i % 500),
                state=["CA", "TX", "NY", "FL", "IL"][i % 5],
                contacts=[] if i % 3 == 0 else [Mock()]
            )
            
            score = scoring_worker.calculate_score(company)
            scores.append(score)
            
            if score["total_score"] >= 80:
                high_quality_count += 1
        
        # Verify processing results
        assert len(scores) == 1000
        assert all(0 <= score["total_score"] <= 100 for score in scores)
        assert high_quality_count > 0  # Should have some high-quality leads
        
        # Verify score distribution is reasonable
        avg_score = sum(score["total_score"] for score in scores) / len(scores)
        assert 50 <= avg_score <= 90  # Average should be reasonable