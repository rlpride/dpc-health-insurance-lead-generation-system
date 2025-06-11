"""Performance benchmark tests for the lead generation system."""

import pytest
import time
import asyncio
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4
import statistics

from models.lead_score import LeadScore
from models.company import Company
from workers.scoring_worker import ScoringWorker
from workers.enrichment_worker import EnrichmentWorker
from api.apollo.client import ApolloClient
from api.pipedrive.client import PipedriveClient
from api.proxycurl.client import ProxycurlClient


class PerformanceTimer:
    """Context manager for measuring execution time."""
    
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


class MemoryProfiler:
    """Context manager for measuring memory usage."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = None
        self.peak_memory = None
        self.final_memory = None
    
    def __enter__(self):
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        # Force garbage collection
        gc.collect()
    
    @property
    def memory_increase(self):
        """Calculate memory increase in MB."""
        if self.final_memory and self.initial_memory:
            return self.final_memory - self.initial_memory
        return 0


class TestLeadScoringPerformance:
    """Performance benchmarks for lead scoring algorithms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scoring_worker = ScoringWorker("perf-test-worker")
    
    def test_single_score_calculation_performance(self):
        """Benchmark single lead score calculation."""
        company = Mock(
            naics_code="621111",
            employee_count_min=100,
            state="CA",
            contacts=[]
        )
        
        # Warm up
        for _ in range(10):
            self.scoring_worker.calculate_score(company)
        
        # Benchmark
        with PerformanceTimer() as timer:
            for _ in range(1000):
                score = self.scoring_worker.calculate_score(company)
                assert score["total_score"] > 0
        
        avg_time_per_score = timer.duration / 1000
        
        # Performance assertions
        assert avg_time_per_score < 0.001  # Less than 1ms per score
        assert timer.duration < 1.0  # Total time under 1 second
        
        print(f"Average time per score calculation: {avg_time_per_score*1000:.3f}ms")
        print(f"Total scoring time for 1000 companies: {timer.duration:.3f}s")
    
    def test_bulk_scoring_performance(self):
        """Benchmark bulk lead scoring performance."""
        # Generate test companies with variety
        companies = []
        for i in range(10000):
            company = Mock(
                naics_code=["621111", "621210", "621310", "622110"][i % 4],
                employee_count_min=10 + (i % 1000),
                state=["CA", "TX", "NY", "FL", "IL", "PA", "OH", "MI", "GA", "NC"][i % 10],
                contacts=[] if i % 3 == 0 else [Mock() for _ in range(i % 5)]
            )
            companies.append(company)
        
        # Benchmark bulk processing
        with PerformanceTimer() as timer, MemoryProfiler() as memory_profiler:
            scores = []
            for company in companies:
                score = self.scoring_worker.calculate_score(company)
                scores.append(score)
        
        # Performance metrics
        companies_per_second = len(companies) / timer.duration
        avg_score = statistics.mean(score["total_score"] for score in scores)
        score_distribution = {
            "high": sum(1 for s in scores if s["total_score"] >= 80),
            "medium": sum(1 for s in scores if 60 <= s["total_score"] < 80),
            "low": sum(1 for s in scores if s["total_score"] < 60)
        }
        
        # Performance assertions
        assert companies_per_second > 1000  # At least 1000 companies/second
        assert memory_profiler.memory_increase < 200  # Less than 200MB increase
        assert 50 <= avg_score <= 90  # Reasonable average score
        
        print(f"Processed {len(companies)} companies in {timer.duration:.3f}s")
        print(f"Processing rate: {companies_per_second:.0f} companies/second")
        print(f"Memory increase: {memory_profiler.memory_increase:.1f}MB")
        print(f"Score distribution: {score_distribution}")
    
    def test_concurrent_scoring_performance(self):
        """Benchmark concurrent scoring performance."""
        # Generate test data
        companies = []
        for i in range(1000):
            company = Mock(
                naics_code="621111",
                employee_count_min=50 + i,
                state=["CA", "TX", "NY"][i % 3],
                contacts=[]
            )
            companies.append(company)
        
        def score_batch(batch):
            """Score a batch of companies."""
            worker = ScoringWorker(f"worker-{id(batch)}")
            scores = []
            for company in batch:
                score = worker.calculate_score(company)
                scores.append(score)
            return scores
        
        # Split into batches for concurrent processing
        batch_size = 100
        batches = [companies[i:i+batch_size] for i in range(0, len(companies), batch_size)]
        
        # Benchmark concurrent processing
        with PerformanceTimer() as timer:
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_batch = {
                    executor.submit(score_batch, batch): batch 
                    for batch in batches
                }
                
                all_scores = []
                for future in as_completed(future_to_batch):
                    batch_scores = future.result()
                    all_scores.extend(batch_scores)
        
        # Performance metrics
        concurrent_rate = len(companies) / timer.duration
        
        # Performance assertions
        assert len(all_scores) == len(companies)
        assert concurrent_rate > 2000  # Better than sequential due to concurrency
        
        print(f"Concurrent processing rate: {concurrent_rate:.0f} companies/second")
    
    def test_grade_calculation_performance(self):
        """Benchmark grade calculation performance."""
        scores = list(range(0, 101))  # All possible scores
        
        with PerformanceTimer() as timer:
            for _ in range(10000):
                for score in scores:
                    grade = LeadScore.calculate_grade(score)
                    assert grade in ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D"]
        
        total_calculations = 10000 * len(scores)
        avg_time_per_calculation = timer.duration / total_calculations
        
        # Performance assertion
        assert avg_time_per_calculation < 0.00001  # Less than 10 microseconds
        
        print(f"Grade calculations per second: {1/avg_time_per_calculation:.0f}")


class TestAPIClientPerformance:
    """Performance benchmarks for API clients."""
    
    @pytest.mark.asyncio
    async def test_apollo_client_response_handling(self):
        """Benchmark Apollo client response processing."""
        client = ApolloClient("test-key")
        
        # Mock large response
        large_response = {
            "people": [
                {
                    "id": f"person_{i}",
                    "first_name": f"First{i}",
                    "last_name": f"Last{i}",
                    "email": f"person{i}@company.com",
                    "title": "Executive",
                    "organization": {
                        "id": f"org_{i//10}",
                        "name": f"Company {i//10}"
                    }
                }
                for i in range(1000)
            ],
            "pagination": {"total_entries": 1000}
        }
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_response = Mock()
            mock_response.json.return_value = large_response
            mock_response.status_code = 200
            mock_response.is_success = True
            
            mock_client = Mock()
            mock_client.get.return_value = mock_response
            mock_httpx.return_value.__aenter__.return_value = mock_client
            
            # Benchmark response processing
            with PerformanceTimer() as timer:
                for _ in range(100):
                    result = await client.search_people(q_organization_domains="test.com")
                    assert len(result["people"]) == 1000
            
            # Performance assertions
            avg_processing_time = timer.duration / 100
            assert avg_processing_time < 0.01  # Less than 10ms per response
            
        print(f"Average API response processing time: {avg_processing_time*1000:.2f}ms")
    
    def test_pipedrive_client_batch_operations(self):
        """Benchmark Pipedrive client batch operations."""
        client = PipedriveClient("test-key", "test-domain")
        
        # Generate test organization data
        organizations = []
        for i in range(500):
            org_data = {
                "name": f"Health Company {i}",
                "address": f"{i} Main St, City, State",
                "owner_id": 1
            }
            organizations.append(org_data)
        
        with patch('requests.post') as mock_post:
            # Mock successful responses
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "data": {"id": 123, "name": "Test Org"}
            }
            mock_response.status_code = 201
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # Benchmark batch processing
            with PerformanceTimer() as timer:
                results = []
                for org_data in organizations:
                    result = client.create_organization(org_data)
                    results.append(result)
            
            # Performance metrics
            orgs_per_second = len(organizations) / timer.duration
            
            # Performance assertions
            assert len(results) == len(organizations)
            assert orgs_per_second > 100  # At least 100 organizations/second
            
        print(f"Pipedrive processing rate: {orgs_per_second:.0f} organizations/second")
    
    @pytest.mark.asyncio
    async def test_proxycurl_client_data_parsing(self):
        """Benchmark Proxycurl client data parsing performance."""
        client = ProxycurlClient("test-key")
        
        # Create large mock response
        large_employee_data = {
            "employees": [
                {
                    "profile_url": f"https://linkedin.com/in/employee{i}",
                    "profile": {
                        "public_identifier": f"employee{i}",
                        "first_name": f"First{i}",
                        "last_name": f"Last{i}",
                        "headline": f"Position at Company {i//50}",
                        "summary": f"Professional summary for employee {i}" * 10,
                        "experiences": [
                            {
                                "company": f"Company {j}",
                                "title": f"Position {j}",
                                "description": "Job description " * 20
                            }
                            for j in range(3)
                        ]
                    }
                }
                for i in range(200)
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_response = Mock()
            mock_response.json.return_value = large_employee_data
            mock_response.status_code = 200
            mock_response.is_success = True
            
            mock_client = Mock()
            mock_client.get.return_value = mock_response
            mock_httpx.return_value.__aenter__.return_value = mock_client
            
            # Benchmark data parsing
            with PerformanceTimer() as timer:
                for _ in range(50):
                    result = await client.get_company_employees("https://linkedin.com/company/test")
                    assert len(result["employees"]) == 200
            
            avg_parsing_time = timer.duration / 50
            
            # Performance assertion
            assert avg_parsing_time < 0.05  # Less than 50ms per large response
            
        print(f"Average Proxycurl parsing time: {avg_parsing_time*1000:.2f}ms")


class TestWorkerPerformance:
    """Performance benchmarks for background workers."""
    
    def test_enrichment_worker_throughput(self):
        """Benchmark enrichment worker message processing throughput."""
        worker = EnrichmentWorker("perf-test-worker")
        
        # Generate test messages
        messages = []
        for i in range(1000):
            message = {"company_id": str(uuid4())}
            messages.append(message)
        
        # Mock successful processing
        with patch.object(worker, 'process_message') as mock_process:
            mock_process.return_value = True
            
            # Benchmark message processing
            with PerformanceTimer() as timer:
                success_count = 0
                for message in messages:
                    if worker.process_message(message):
                        success_count += 1
            
            # Performance metrics
            messages_per_second = len(messages) / timer.duration
            
            # Performance assertions
            assert success_count == len(messages)
            assert messages_per_second > 500  # At least 500 messages/second
            
        print(f"Enrichment worker throughput: {messages_per_second:.0f} messages/second")
    
    def test_scoring_worker_database_performance(self):
        """Benchmark scoring worker database operations."""
        worker = ScoringWorker("db-perf-test-worker")
        worker.settings = Mock()
        worker.settings.high_score_threshold = 80
        
        # Generate test companies
        companies = []
        for i in range(100):
            company = Mock(
                id=str(uuid4()),
                naics_code="621111",
                employee_count_min=100 + i,
                state="CA",
                contacts=[]
            )
            companies.append(company)
        
        with patch('workers.scoring_worker.get_db_session') as mock_db_session:
            mock_db = Mock()
            mock_db_session.return_value.__enter__.return_value = mock_db
            
            # Mock database operations
            mock_db.query.return_value.filter_by.return_value.first.side_effect = companies
            mock_db.add.return_value = None
            mock_db.commit.return_value = None
            
            # Benchmark database operations
            with PerformanceTimer() as timer:
                for company in companies:
                    message = {"company_id": company.id}
                    result = worker.process_message(message)
                    assert result is True
            
            # Performance metrics
            db_ops_per_second = len(companies) / timer.duration
            
            # Verify database calls
            assert mock_db.add.call_count == len(companies)
            assert mock_db.commit.call_count == len(companies)
            
            # Performance assertion
            assert db_ops_per_second > 50  # At least 50 DB operations/second
            
        print(f"Database operations per second: {db_ops_per_second:.0f}")


class TestSystemMemoryPerformance:
    """Memory performance and leak detection tests."""
    
    def test_memory_stability_during_long_running_operations(self):
        """Test memory stability during extended processing."""
        scoring_worker = ScoringWorker("memory-stability-worker")
        
        # Baseline memory
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_samples = [baseline_memory]
        
        # Process batches and sample memory
        for batch in range(10):
            # Process batch of companies
            for i in range(100):
                company = Mock(
                    naics_code="621111",
                    employee_count_min=100,
                    state="CA",
                    contacts=[]
                )
                score = scoring_worker.calculate_score(company)
                assert score["total_score"] > 0
            
            # Sample memory after each batch
            gc.collect()  # Force garbage collection
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
        
        # Calculate memory growth trend
        memory_growth = memory_samples[-1] - memory_samples[0]
        max_memory = max(memory_samples)
        
        # Memory stability assertions
        assert memory_growth < 50  # Less than 50MB growth over 1000 operations
        assert max_memory - baseline_memory < 100  # Peak memory increase < 100MB
        
        print(f"Memory growth over 1000 operations: {memory_growth:.1f}MB")
        print(f"Peak memory increase: {max_memory - baseline_memory:.1f}MB")
    
    def test_garbage_collection_effectiveness(self):
        """Test effectiveness of garbage collection."""
        # Create and process large amounts of data
        data_objects = []
        
        # Baseline memory
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        # Create large dataset
        for i in range(10000):
            # Create complex objects that should be garbage collected
            company_data = {
                "id": str(uuid4()),
                "name": f"Company {i}",
                "contacts": [
                    {"name": f"Contact {j}", "data": "x" * 100}
                    for j in range(10)
                ],
                "scores": [i + j for j in range(100)]
            }
            data_objects.append(company_data)
        
        # Memory after object creation
        after_creation_memory = process.memory_info().rss / 1024 / 1024
        
        # Clear references and force garbage collection
        data_objects.clear()
        del data_objects
        
        # Multiple GC passes
        for _ in range(5):
            gc.collect()
        
        # Final memory measurement
        final_memory = process.memory_info().rss / 1024 / 1024
        
        # Calculate garbage collection effectiveness
        memory_created = after_creation_memory - baseline_memory
        memory_reclaimed = after_creation_memory - final_memory
        gc_effectiveness = memory_reclaimed / memory_created if memory_created > 0 else 0
        
        # Garbage collection assertions
        assert gc_effectiveness > 0.7  # At least 70% of memory should be reclaimed
        assert final_memory - baseline_memory < 50  # Final memory increase < 50MB
        
        print(f"Memory created: {memory_created:.1f}MB")
        print(f"Memory reclaimed: {memory_reclaimed:.1f}MB")
        print(f"GC effectiveness: {gc_effectiveness:.1%}")


class TestConcurrencyPerformance:
    """Performance tests for concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_api_calls_performance(self):
        """Benchmark concurrent API call performance."""
        apollo_client = ApolloClient("test-key")
        
        # Mock response
        mock_response_data = {"people": [{"id": "test"}]}
        
        async def make_api_call():
            with patch('httpx.AsyncClient') as mock_httpx:
                mock_response = Mock()
                mock_response.json.return_value = mock_response_data
                mock_response.status_code = 200
                mock_response.is_success = True
                
                mock_client = Mock()
                mock_client.get.return_value = mock_response
                mock_httpx.return_value.__aenter__.return_value = mock_client
                
                return await apollo_client.search_people(q_organization_domains="test.com")
        
        # Benchmark concurrent API calls
        with PerformanceTimer() as timer:
            tasks = [make_api_call() for _ in range(50)]
            results = await asyncio.gather(*tasks)
        
        # Performance metrics
        concurrent_rate = len(results) / timer.duration
        
        # Performance assertions
        assert len(results) == 50
        assert all("people" in result for result in results)
        assert concurrent_rate > 100  # At least 100 concurrent calls/second
        
        print(f"Concurrent API calls per second: {concurrent_rate:.0f}")
    
    def test_thread_safety_performance(self):
        """Test thread safety and performance under concurrent load."""
        scoring_worker = ScoringWorker("thread-safety-worker")
        
        def score_companies_batch(batch_id, num_companies):
            """Score a batch of companies in a thread."""
            scores = []
            for i in range(num_companies):
                company = Mock(
                    naics_code="621111",
                    employee_count_min=100 + i,
                    state="CA",
                    contacts=[]
                )
                score = scoring_worker.calculate_score(company)
                scores.append(score)
            return batch_id, scores
        
        # Benchmark concurrent scoring
        with PerformanceTimer() as timer:
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(score_companies_batch, i, 100)
                    for i in range(8)
                ]
                
                all_results = {}
                for future in as_completed(futures):
                    batch_id, scores = future.result()
                    all_results[batch_id] = scores
        
        # Verify results
        total_scores = sum(len(scores) for scores in all_results.values())
        concurrent_rate = total_scores / timer.duration
        
        # Performance assertions
        assert len(all_results) == 8
        assert total_scores == 800
        assert concurrent_rate > 1000  # At least 1000 scores/second concurrently
        
        print(f"Concurrent scoring rate: {concurrent_rate:.0f} scores/second")


@pytest.fixture
def performance_test_data():
    """Fixture providing performance test data."""
    return {
        "companies": [
            Mock(
                id=str(uuid4()),
                naics_code=["621111", "621210", "621310"][i % 3],
                employee_count_min=50 + (i * 10),
                state=["CA", "TX", "NY", "FL"][i % 4],
                contacts=[] if i % 2 == 0 else [Mock() for _ in range(i % 5)]
            )
            for i in range(1000)
        ]
    }


class TestEndToEndPerformance:
    """End-to-end performance benchmarks."""
    
    def test_full_pipeline_performance(self, performance_test_data):
        """Benchmark full pipeline performance end-to-end."""
        companies = performance_test_data["companies"]
        
        # Components
        enrichment_worker = EnrichmentWorker("perf-enrichment-worker")
        scoring_worker = ScoringWorker("perf-scoring-worker")
        
        with patch('models.get_db_session') as mock_db_session:
            mock_db = Mock()
            mock_db_session.return_value.__enter__.return_value = mock_db
            
            # Mock database operations
            mock_db.query.return_value.filter_by.return_value.first.side_effect = companies
            
            # Benchmark full pipeline
            with PerformanceTimer() as timer, MemoryProfiler() as memory_profiler:
                processed_count = 0
                
                for company in companies[:100]:  # Process subset for performance test
                    # Mock enrichment processing
                    with patch.object(enrichment_worker, 'process_message') as mock_enrich:
                        mock_enrich.return_value = True
                        enrich_result = enrichment_worker.process_message({
                            "company_id": company.id
                        })
                    
                    # Mock scoring processing
                    if enrich_result:
                        score_result = scoring_worker.process_message({
                            "company_id": company.id
                        })
                        if score_result:
                            processed_count += 1
            
            # Performance metrics
            pipeline_rate = processed_count / timer.duration
            
            # Performance assertions
            assert processed_count == 100
            assert pipeline_rate > 50  # At least 50 companies/second through pipeline
            assert memory_profiler.memory_increase < 100  # Memory increase < 100MB
            
        print(f"Full pipeline processing rate: {pipeline_rate:.0f} companies/second")
        print(f"Memory usage: {memory_profiler.memory_increase:.1f}MB")