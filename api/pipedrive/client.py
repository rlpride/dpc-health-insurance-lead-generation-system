"""Pipedrive CRM API client implementation."""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PipedriveError(Exception):
    """Base exception for Pipedrive API errors."""
    pass


class PipedriveRateLimitError(PipedriveError):
    """Exception raised when rate limit is exceeded."""
    pass


class PipedriveResponse(BaseModel):
    """Standard Pipedrive API response model."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    additional_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[int] = None


class PipedriveClient:
    """Comprehensive client for Pipedrive CRM API with rate limiting and retries."""
    
    def __init__(self, api_key: str, domain: str, rate_limit_per_second: float = 1.0):
        """Initialize Pipedrive client.
        
        Args:
            api_key: Pipedrive API key
            domain: Pipedrive domain (e.g., 'your-company')
            rate_limit_per_second: Maximum API calls per second
        """
        self.api_key = api_key
        self.domain = domain
        self.base_url = f"https://{domain}.pipedrive.com/api/v1"
        self.rate_limit_per_second = rate_limit_per_second
        self._last_request_time = datetime.now()
        
        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    async def _rate_limit(self):
        """Implement rate limiting."""
        now = datetime.now()
        time_since_last = (now - self._last_request_time).total_seconds()
        min_interval = 1.0 / self.rate_limit_per_second
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = datetime.now()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, PipedriveRateLimitError))
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> PipedriveResponse:
        """Make HTTP request to Pipedrive API with rate limiting and retries."""
        await self._rate_limit()
        
        url = f"{self.base_url}/{endpoint}"
        request_params = {"api_token": self.api_key}
        if params:
            request_params.update(params)
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                params=request_params,
                json=data if data else None
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("Rate limit exceeded, retrying...")
                raise PipedriveRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            response_data = response.json()
            
            return PipedriveResponse(**response_data)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise PipedriveError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise
    
    async def create_organization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an organization in Pipedrive.
        
        Args:
            data: Organization data including name, address, etc.
            
        Returns:
            Created organization data with ID
        """
        response = await self._make_request("POST", "organizations", data=data)
        
        if not response.success:
            raise PipedriveError(f"Failed to create organization: {response.error}")
        
        logger.info(f"Created organization: {data.get('name')} (ID: {response.data.get('id') if response.data else 'Unknown'})")
        return response.data or {}
    
    async def update_organization(self, org_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an organization in Pipedrive."""
        response = await self._make_request("PUT", f"organizations/{org_id}", data=data)
        
        if not response.success:
            raise PipedriveError(f"Failed to update organization {org_id}: {response.error}")
        
        logger.info(f"Updated organization ID: {org_id}")
        return response.data or {}
    
    async def create_person(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a person (contact) in Pipedrive.
        
        Args:
            data: Person data including name, email, org_id, etc.
            
        Returns:
            Created person data with ID
        """
        response = await self._make_request("POST", "persons", data=data)
        
        if not response.success:
            raise PipedriveError(f"Failed to create person: {response.error}")
        
        logger.info(f"Created person: {data.get('name')} (ID: {response.data.get('id') if response.data else 'Unknown'})")
        return response.data or {}
    
    async def update_person(self, person_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a person in Pipedrive."""
        response = await self._make_request("PUT", f"persons/{person_id}", data=data)
        
        if not response.success:
            raise PipedriveError(f"Failed to update person {person_id}: {response.error}")
        
        logger.info(f"Updated person ID: {person_id}")
        return response.data or {}
    
    async def create_deal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deal in Pipedrive.
        
        Args:
            data: Deal data including title, org_id, person_id, value, etc.
            
        Returns:
            Created deal data with ID
        """
        response = await self._make_request("POST", "deals", data=data)
        
        if not response.success:
            raise PipedriveError(f"Failed to create deal: {response.error}")
        
        logger.info(f"Created deal: {data.get('title')} (ID: {response.data.get('id') if response.data else 'Unknown'})")
        return response.data or {}
    
    async def get_organization_fields(self) -> List[Dict[str, Any]]:
        """Get all organization custom fields."""
        response = await self._make_request("GET", "organizationFields")
        
        if not response.success:
            raise PipedriveError(f"Failed to get organization fields: {response.error}")
        
        return response.data or []
    
    async def get_person_fields(self) -> List[Dict[str, Any]]:
        """Get all person custom fields."""
        response = await self._make_request("GET", "personFields")
        
        if not response.success:
            raise PipedriveError(f"Failed to get person fields: {response.error}")
        
        return response.data or []
    
    async def get_deal_fields(self) -> List[Dict[str, Any]]:
        """Get all deal custom fields."""
        response = await self._make_request("GET", "dealFields")
        
        if not response.success:
            raise PipedriveError(f"Failed to get deal fields: {response.error}")
        
        return response.data or []
    
    async def create_custom_field(
        self, 
        field_type: str,  # 'org', 'person', 'deal'
        name: str,
        field_data_type: str = "varchar",
        options: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a custom field in Pipedrive.
        
        Args:
            field_type: Type of field ('org', 'person', 'deal')
            name: Field name
            field_data_type: Data type (varchar, int, double, etc.)
            options: Options for enum fields
        """
        endpoint_map = {
            'org': 'organizationFields',
            'person': 'personFields', 
            'deal': 'dealFields'
        }
        
        endpoint = endpoint_map.get(field_type)
        if not endpoint:
            raise ValueError(f"Invalid field_type: {field_type}")
        
        data = {
            "name": name,
            "field_type": field_data_type
        }
        
        if options:
            data["options"] = options
        
        response = await self._make_request("POST", endpoint, data=data)
        
        if not response.success:
            raise PipedriveError(f"Failed to create custom field: {response.error}")
        
        logger.info(f"Created custom field: {name} for {field_type}")
        return response.data or {}
    
    async def search_organizations(self, term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for organizations by name."""
        params = {"term": term, "limit": limit}
        response = await self._make_request("GET", "organizations/search", params=params)
        
        if not response.success:
            logger.warning(f"Organization search failed: {response.error}")
            return []
        
        return response.data.get("items", []) if response.data else []
    
    async def search_persons(self, term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for persons by name or email."""
        params = {"term": term, "limit": limit}
        response = await self._make_request("GET", "persons/search", params=params)
        
        if not response.success:
            logger.warning(f"Person search failed: {response.error}")
            return []
        
        return response.data.get("items", []) if response.data else [] 