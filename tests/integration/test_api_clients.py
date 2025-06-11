"""Integration tests for API clients with mocked external responses."""

import pytest
import httpx
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

from api.apollo.client import ApolloClient
from api.pipedrive.client import PipedriveClient  
from api.proxycurl.client import ProxycurlClient


class TestApolloClientIntegration:
    """Integration tests for Apollo API client."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = ApolloClient(api_key="test-apollo-key")
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_search_people_success(self, mock_httpx):
        """Test successful people search with mocked API response."""
        # Mock response data
        mock_response_data = {
            "people": [
                {
                    "id": "person_123",
                    "first_name": "John",
                    "last_name": "Doe", 
                    "title": "CEO",
                    "email": "john.doe@healthcorp.com",
                    "linkedin_url": "https://linkedin.com/in/johndoe",
                    "organization": {
                        "id": "org_456",
                        "name": "HealthCorp Insurance",
                        "website_url": "https://healthcorp.com"
                    }
                },
                {
                    "id": "person_789",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "title": "VP Sales",
                    "email": "jane.smith@healthcorp.com",
                    "linkedin_url": "https://linkedin.com/in/janesmith",
                    "organization": {
                        "id": "org_456", 
                        "name": "HealthCorp Insurance",
                        "website_url": "https://healthcorp.com"
                    }
                }
            ],
            "pagination": {
                "page": 1,
                "per_page": 25,
                "total_entries": 2,
                "total_pages": 1
            }
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        mock_response.is_success = True
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Test search
        result = await self.client.search_people(
            q_organization_domains="healthcorp.com",
            person_titles=["CEO", "VP"],
            organization_locations=["United States"]
        )
        
        # Assertions
        assert "people" in result
        assert len(result["people"]) == 2
        
        # Check first person
        person1 = result["people"][0]
        assert person1["first_name"] == "John"
        assert person1["last_name"] == "Doe"
        assert person1["title"] == "CEO"
        assert person1["email"] == "john.doe@healthcorp.com"
        
        # Check API call was made correctly
        mock_client.get.assert_called_once()
        call_url = mock_client.get.call_args[0][0]
        assert "people/search" in call_url
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_search_people_api_error(self, mock_httpx):
        """Test API error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.is_success = False
        mock_response.json.return_value = {"error": "Invalid API key"}
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        with pytest.raises(httpx.HTTPStatusError):
            await self.client.search_people(q_organization_domains="test.com")
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_search_people_network_error(self, mock_httpx):
        """Test network error handling."""
        mock_client = Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        with pytest.raises(httpx.ConnectError):
            await self.client.search_people(q_organization_domains="test.com")
    
    @pytest.mark.asyncio
    async def test_search_people_empty_results(self):
        """Test search with no results."""
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_response = Mock()
            mock_response.json.return_value = {
                "people": [],
                "pagination": {"total_entries": 0}
            }
            mock_response.status_code = 200
            mock_response.is_success = True
            
            mock_client = Mock()
            mock_client.get.return_value = mock_response
            mock_httpx.return_value.__aenter__.return_value = mock_client
            
            result = await self.client.search_people(
                q_organization_domains="nonexistent.com"
            )
            
            assert result["people"] == []
            assert result["pagination"]["total_entries"] == 0


class TestPipedriveClientIntegration:
    """Integration tests for Pipedrive API client."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = PipedriveClient(
            api_key="test-pipedrive-key",
            domain="healthinsurance"
        )
    
    @patch('requests.post')
    def test_create_organization_success(self, mock_post):
        """Test successful organization creation."""
        # Mock response data
        mock_response_data = {
            "success": True,
            "data": {
                "id": 123,
                "name": "HealthCorp Insurance",
                "address": "123 Main St, New York, NY",
                "owner_id": 1,
                "add_time": "2024-01-15 10:30:00",
                "update_time": "2024-01-15 10:30:00",
                "visible_to": "3",
                "label": None
            }
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 201
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Test organization creation
        org_data = {
            "name": "HealthCorp Insurance",
            "address": "123 Main St, New York, NY",
            "owner_id": 1
        }
        
        result = self.client.create_organization(org_data)
        
        # Assertions
        assert result["success"] is True
        assert result["data"]["id"] == 123
        assert result["data"]["name"] == "HealthCorp Insurance"
        
        # Check API call
        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert "organizations" in call_url
        assert "api_token=test-pipedrive-key" in call_url
    
    @patch('requests.post')
    def test_create_organization_api_error(self, mock_post):
        """Test API error during organization creation."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "error": "Name is required",
            "error_info": "The name field cannot be empty"
        }
        mock_response.raise_for_status.side_effect = Exception("Bad Request")
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception):
            self.client.create_organization({"address": "123 Main St"})
    
    @patch('requests.post')
    def test_create_organization_network_error(self, mock_post):
        """Test network error during organization creation."""
        mock_post.side_effect = Exception("Connection timeout")
        
        with pytest.raises(Exception):
            self.client.create_organization({"name": "Test Org"})
    
    @patch('requests.get')
    def test_get_organization_success(self, mock_get):
        """Test successful organization retrieval."""
        mock_response_data = {
            "success": True,
            "data": {
                "id": 123,
                "name": "HealthCorp Insurance",
                "people_count": 150,
                "activities_count": 25,
                "done_activities_count": 20,
                "undone_activities_count": 5
            }
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.client.get_organization(123)
        
        assert result["success"] is True
        assert result["data"]["name"] == "HealthCorp Insurance"
        assert result["data"]["people_count"] == 150


class TestProxycurlClientIntegration:
    """Integration tests for Proxycurl API client."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = ProxycurlClient(api_key="test-proxycurl-key")
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_company_employees_success(self, mock_httpx):
        """Test successful company employees retrieval."""
        # Mock response data
        mock_response_data = {
            "employees": [
                {
                    "profile_url": "https://linkedin.com/in/johndoe",
                    "profile": {
                        "public_identifier": "johndoe",
                        "first_name": "John",
                        "last_name": "Doe",
                        "full_name": "John Doe",
                        "headline": "CEO at HealthCorp Insurance",
                        "summary": "Leading digital transformation in healthcare...",
                        "country": "United States",
                        "city": "New York",
                        "experiences": [
                            {
                                "company": "HealthCorp Insurance",
                                "title": "CEO",
                                "description": "Leading the company...",
                                "starts_at": {"day": 1, "month": 1, "year": 2020},
                                "ends_at": None
                            }
                        ]
                    }
                },
                {
                    "profile_url": "https://linkedin.com/in/janesmith",
                    "profile": {
                        "public_identifier": "janesmith", 
                        "first_name": "Jane",
                        "last_name": "Smith",
                        "full_name": "Jane Smith",
                        "headline": "VP of Sales at HealthCorp Insurance",
                        "country": "United States",
                        "city": "Boston"
                    }
                }
            ],
            "next_page": None,
            "total_result_count": 2
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        mock_response.is_success = True
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Test company employees search
        result = await self.client.get_company_employees(
            company_url="https://linkedin.com/company/healthcorp-insurance"
        )
        
        # Assertions
        assert "employees" in result
        assert len(result["employees"]) == 2
        
        # Check first employee
        employee1 = result["employees"][0]
        assert employee1["profile"]["first_name"] == "John"
        assert employee1["profile"]["last_name"] == "Doe"
        assert employee1["profile"]["headline"] == "CEO at HealthCorp Insurance"
        
        # Check API call
        mock_client.get.assert_called_once()
        call_url = mock_client.get.call_args[0][0]
        assert "company" in call_url
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_company_employees_rate_limit(self, mock_httpx):
        """Test rate limiting handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.is_success = False
        mock_response.json.return_value = {
            "error": "Rate limit exceeded",
            "retry_after": 60
        }
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        with pytest.raises(httpx.HTTPStatusError):
            await self.client.get_company_employees(
                "https://linkedin.com/company/test"
            )
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_company_profile_success(self, mock_httpx):
        """Test successful company profile retrieval."""
        mock_response_data = {
            "linkedin_internal_id": "1234567",
            "description": "Leading health insurance provider...",
            "website": "https://healthcorp.com",
            "industry": "Insurance",
            "company_size": [501, 1000],
            "company_size_on_linkedin": 850,
            "hq": {
                "country": "United States",
                "city": "New York",
                "postal_code": "10001",
                "line_1": "123 Main Street"
            },
            "company_type": "PUBLIC_COMPANY",
            "founded_year": 1995,
            "specialities": [
                "Health Insurance",
                "Medical Coverage", 
                "Employee Benefits"
            ],
            "locations": [
                {
                    "country": "United States",
                    "city": "New York",
                    "is_hq": True
                },
                {
                    "country": "United States", 
                    "city": "Boston",
                    "is_hq": False
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        mock_response.is_success = True
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        result = await self.client.get_company_profile(
            "https://linkedin.com/company/healthcorp-insurance"
        )
        
        assert result["industry"] == "Insurance"
        assert result["company_size"] == [501, 1000]
        assert result["founded_year"] == 1995
        assert len(result["specialities"]) == 3
        assert len(result["locations"]) == 2


class TestAPIClientErrorHandling:
    """Test error handling across all API clients."""
    
    @pytest.mark.asyncio
    async def test_apollo_timeout_handling(self):
        """Test Apollo client timeout handling."""
        client = ApolloClient("test-key")
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = Mock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
            mock_httpx.return_value.__aenter__.return_value = mock_client
            
            with pytest.raises(httpx.TimeoutException):
                await client.search_people(q_organization_domains="test.com")
    
    def test_pipedrive_authentication_error(self):
        """Test Pipedrive authentication error handling."""
        client = PipedriveClient("invalid-key", "test-domain")
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "success": False,
                "error": "Unauthorized",
                "error_info": "Invalid API token"
            }
            mock_response.raise_for_status.side_effect = Exception("Unauthorized")
            mock_post.return_value = mock_response
            
            with pytest.raises(Exception):
                client.create_organization({"name": "Test"})
    
    @pytest.mark.asyncio
    async def test_proxycurl_credit_exhausted(self):
        """Test Proxycurl credit exhausted error."""
        client = ProxycurlClient("test-key")
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 402
            mock_response.is_success = False
            mock_response.json.return_value = {
                "error": "Insufficient credits"
            }
            
            mock_client = Mock()
            mock_client.get.return_value = mock_response
            mock_httpx.return_value.__aenter__.return_value = mock_client
            
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_company_employees("https://linkedin.com/company/test")


@pytest.fixture
def mock_api_responses():
    """Fixture providing mock API responses for testing."""
    return {
        "apollo_people_search": {
            "people": [
                {
                    "id": "test_person_1",
                    "first_name": "Test",
                    "last_name": "User",
                    "email": "test@example.com"
                }
            ]
        },
        "pipedrive_org_create": {
            "success": True,
            "data": {"id": 123, "name": "Test Organization"}
        },
        "proxycurl_employees": {
            "employees": [
                {
                    "profile": {
                        "first_name": "Test",
                        "last_name": "Employee"
                    }
                }
            ]
        }
    }


class TestAPIClientIntegrationScenarios:
    """End-to-end integration scenarios for API clients."""
    
    @pytest.mark.asyncio
    async def test_lead_enrichment_workflow(self, mock_api_responses):
        """Test complete lead enrichment workflow using all API clients."""
        apollo_client = ApolloClient("test-apollo-key")
        pipedrive_client = PipedriveClient("test-pipedrive-key", "test-domain")
        proxycurl_client = ProxycurlClient("test-proxycurl-key")
        
        # Mock all external API calls
        with patch('httpx.AsyncClient') as mock_httpx_apollo, \
             patch('requests.post') as mock_pipedrive_post, \
             patch('httpx.AsyncClient') as mock_httpx_proxycurl:
            
            # Apollo mock
            apollo_response = Mock()
            apollo_response.json.return_value = mock_api_responses["apollo_people_search"]
            apollo_response.status_code = 200
            apollo_response.is_success = True
            
            mock_apollo_client = Mock()
            mock_apollo_client.get.return_value = apollo_response
            mock_httpx_apollo.return_value.__aenter__.return_value = mock_apollo_client
            
            # Pipedrive mock
            pipedrive_response = Mock()
            pipedrive_response.json.return_value = mock_api_responses["pipedrive_org_create"]
            pipedrive_response.status_code = 201
            pipedrive_response.raise_for_status.return_value = None
            mock_pipedrive_post.return_value = pipedrive_response
            
            # Proxycurl mock
            proxycurl_response = Mock()
            proxycurl_response.json.return_value = mock_api_responses["proxycurl_employees"]
            proxycurl_response.status_code = 200
            proxycurl_response.is_success = True
            
            mock_proxycurl_client = Mock()
            mock_proxycurl_client.get.return_value = proxycurl_response
            mock_httpx_proxycurl.return_value.__aenter__.return_value = mock_proxycurl_client
            
            # Execute workflow
            # 1. Search for people via Apollo
            apollo_result = await apollo_client.search_people(
                q_organization_domains="example.com"
            )
            
            # 2. Create organization in Pipedrive
            pipedrive_result = pipedrive_client.create_organization({
                "name": "Example Company"
            })
            
            # 3. Get employee details via Proxycurl
            proxycurl_result = await proxycurl_client.get_company_employees(
                "https://linkedin.com/company/example"
            )
            
            # Verify workflow results
            assert len(apollo_result["people"]) == 1
            assert pipedrive_result["success"] is True
            assert len(proxycurl_result["employees"]) == 1
            
            # Verify all APIs were called
            mock_apollo_client.get.assert_called_once()
            mock_pipedrive_post.assert_called_once()
            mock_proxycurl_client.get.assert_called_once()