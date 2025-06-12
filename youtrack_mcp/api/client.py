"""
Base client for YouTrack REST API.
"""
import logging
import time
from typing import Any, Dict, List, Optional, Union
import json
import random

import requests
from pydantic import BaseModel, Field, model_validator

from youtrack_mcp.config import config

logger = logging.getLogger(__name__)


class YouTrackAPIError(Exception):
    """Base exception for YouTrack API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[requests.Response] = None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class RateLimitError(YouTrackAPIError):
    """Exception for API rate limiting errors."""
    pass


class ResourceNotFoundError(YouTrackAPIError):
    """Exception for 404 Not Found errors."""
    pass


class AuthenticationError(YouTrackAPIError):
    """Exception for authentication errors."""
    pass


class PermissionDeniedError(YouTrackAPIError):
    """Exception for permission-related errors."""
    pass


class ValidationError(YouTrackAPIError):
    """Exception for validation errors in API requests."""
    pass


class ServerError(YouTrackAPIError):
    """Exception for server-side errors."""
    pass


class YouTrackModel(BaseModel):
    """Base model for YouTrack API resources."""
    
    id: str
    
    class Config:
        """Pydantic configuration for YouTrack models."""
        
        extra = "allow"  # Allow extra fields in the model
        populate_by_name = True  # Allow population by field name


class YouTrackClient:
    """Base client for YouTrack REST API."""
    
    def __init__(self, base_url: Optional[str] = None, api_token: Optional[str] = None, 
                 verify_ssl: Optional[bool] = None, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize YouTrack API client.
        
        Args:
            base_url: YouTrack instance URL, defaults to config.get_base_url()
            api_token: API token for authentication, defaults to config.YOUTRACK_API_TOKEN
            verify_ssl: Whether to verify SSL certificates, defaults to config.VERIFY_SSL
            max_retries: Maximum number of retries for transient errors
            retry_delay: Initial delay between retries in seconds (increases exponentially)
        """
        self.base_url = base_url or config.get_base_url()
        self.api_token = api_token or config.YOUTRACK_API_TOKEN
        self.verify_ssl = verify_ssl if verify_ssl is not None else config.VERIFY_SSL
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Validate required configuration
        if not self.api_token:
            raise ValueError("API token is required")
        
        # Session for connection pooling and header reuse
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        
        # Set SSL verification options
        self.session.verify = self.verify_ssl
        if not self.verify_ssl:
            # Use the custom SSL context
            self.session.verify = False
            # Suppress insecure request warnings
            from requests.packages.urllib3.exceptions import InsecureRequestWarning
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        
        logger.debug(f"YouTrack client initialized for {'YouTrack Cloud' if config.is_cloud_instance() else self.base_url}")
        
        # Cache for field definitions to avoid repeated API calls
        self._field_cache = {}
    
    def _get_api_url(self, endpoint: str) -> str:
        """
        Construct full API URL from endpoint.
        
        Args:
            endpoint: API endpoint (without leading slash)
            
        Returns:
            Full API URL
        """
        if self.base_url.endswith('/api'):
            return f"{self.base_url}/{endpoint}"
        else:
            return f"{self.base_url}/api/{endpoint}"
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response, raising appropriate exceptions for errors.
        
        Args:
            response: Response from API
            
        Returns:
            Parsed JSON response
            
        Raises:
            Various exceptions based on response status
        """
        status_code = response.status_code
        
        # Handle success
        if 200 <= status_code < 300:
            # Some endpoints return empty responses
            if not response.content or response.content.strip() == b'':
                return {}
            
            try:
                return response.json()
            except json.JSONDecodeError:
                # Handle non-JSON responses
                logger.warning(f"Non-JSON response received from API: {response.content[:100]}")
                return {"raw_content": response.content.decode("utf-8", errors="replace")}
        
        # Handle error responses
        error_message = f"API request failed with status {status_code}"
        
        # Try to extract error details from response
        try:
            error_data = response.json()
            if isinstance(error_data, dict) and "error" in error_data:
                error_message = f"{error_message}: {error_data['error']}"
        except (json.JSONDecodeError, KeyError):
            if response.content:
                error_message = f"{error_message}: {response.content.decode('utf-8', errors='replace')}"
        
        # Raise appropriate exception based on status code
        if status_code == 400:
            raise ValidationError(error_message, status_code, response)
        elif status_code == 401:
            raise AuthenticationError(error_message, status_code, response)
        elif status_code == 403:
            raise PermissionDeniedError(error_message, status_code, response)
        elif status_code == 404:
            raise ResourceNotFoundError(error_message, status_code, response)
        elif status_code == 429:
            raise RateLimitError(error_message, status_code, response)
        elif 500 <= status_code < 600:
            raise ServerError(error_message, status_code, response)
        else:
            raise YouTrackAPIError(error_message, status_code, response)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make API request with retry logic for transient errors.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Parsed JSON response
            
        Raises:
            YouTrackAPIError: For non-transient errors or if all retries fail
        """
        url = self._get_api_url(endpoint)
        retries = 0
        delay = self.retry_delay
        last_error = None
        
        # For debugging purposes, log essential request details
        if 'json' in kwargs:
            logger.debug(f"{method} {url} with JSON: {json.dumps(kwargs['json'])}")
        elif 'data' in kwargs:
            logger.debug(f"{method} {url} with data: {kwargs['data']}")
        else:
            logger.debug(f"{method} {url}")
            
        while retries <= self.max_retries:
            try:
                response = self.session.request(method, url, **kwargs)
                return self._handle_response(response)
            except (ServerError, RateLimitError) as e:
                # These are potentially transient, so we retry
                last_error = e
                retries += 1
                
                if retries > self.max_retries:
                    logger.error(f"Maximum retries reached for {method} {url}")
                    break
                
                # Calculate backoff delay (exponential with jitter)
                backoff = delay * (2 ** retries) * (0.5 + 0.5 * random.random())
                logger.warning(f"Transient error, retrying in {backoff:.2f}s: {str(e)}")
                time.sleep(backoff)
            except YouTrackAPIError as e:
                # Non-transient errors
                logger.error(f"API error for {method} {url}: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_content = e.response.content.decode('utf-8', errors='replace')
                        logger.error(f"Response content: {error_content}")
                    except:
                        pass
                raise
            except Exception as e:
                # Unexpected errors
                logger.exception(f"Unexpected error for {method} {url}: {str(e)}")
                raise YouTrackAPIError(f"Unexpected error: {str(e)}")
        
        # If we got here, we've exceeded retries
        if last_error:
            raise last_error
        
        # This should never happen, but just in case
        raise YouTrackAPIError(f"Maximum retries exceeded for {method} {url}")
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Make GET request to API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Parsed JSON response
        """
        return self._make_request("GET", endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Make POST request to API.
        
        Args:
            endpoint: API endpoint
            data: Form data
            json_data: JSON data
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Parsed JSON response
        """
        # If data is provided but json_data is not, use data as json
        if data is not None and json_data is None:
            # Log the data being sent for debugging
            logger.debug(f"POST {endpoint} with data: {json.dumps(data)}")
            
            # Some endpoints expect parameters in different formats
            # YouTrack API usually expects data as JSON
            return self._make_request("POST", endpoint, json=data, **kwargs)
        
        return self._make_request("POST", endpoint, data=data, json=json_data, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Make PUT request to API.
        
        Args:
            endpoint: API endpoint
            data: Form data
            json_data: JSON data
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Parsed JSON response
        """
        return self._make_request("PUT", endpoint, data=data, json=json_data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make DELETE request to API.
        
        Args:
            endpoint: API endpoint
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Parsed JSON response
        """
        return self._make_request("DELETE", endpoint, **kwargs)
    
    def close(self) -> None:
        """Close the API client session."""
        self.session.close()
        
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager, closing session."""
        self.close()
    
    def get_enum_bundle_elements(self, bundle_id: str) -> Dict[str, Any]:
        """
        Get enum bundle elements by bundle ID with caching.
        
        Args:
            bundle_id: The bundle ID for the enum field
            
        Returns:
            Dictionary containing enum bundle elements
        """
        cache_key = f"enum_bundle_{bundle_id}"
        if cache_key in self._field_cache:
            return self._field_cache[cache_key]
        
        try:
            # Get enum bundle elements with values
            fields = "values(id,name,description,ordinal)"
            response = self.get(f"admin/customFieldSettings/bundles/enum/{bundle_id}?fields={fields}")
            self._field_cache[cache_key] = response
            return response
        except Exception as e:
            logger.warning(f"Failed to get enum bundle {bundle_id}: {str(e)}")
            return {}
    
    def get_state_bundle_elements(self, bundle_id: str) -> Dict[str, Any]:
        """
        Get state bundle elements by bundle ID with caching.
        
        Args:
            bundle_id: The bundle ID for the state field
            
        Returns:
            Dictionary containing state bundle elements
        """
        cache_key = f"state_bundle_{bundle_id}"
        if cache_key in self._field_cache:
            return self._field_cache[cache_key]
        
        try:
            # Get state bundle elements with values
            fields = "values(id,name,description,isResolved)"
            response = self.get(f"admin/customFieldSettings/bundles/state/{bundle_id}?fields={fields}")
            self._field_cache[cache_key] = response
            return response
        except Exception as e:
            logger.warning(f"Failed to get state bundle {bundle_id}: {str(e)}")
            return {}
    
    def get_project_custom_fields(self, project_id: str) -> Dict[str, Any]:
        """
        Get custom field definitions for a project with caching.
        
        Args:
            project_id: The project ID
            
        Returns:
            Dictionary containing project custom field definitions
        """
        cache_key = f"project_fields_{project_id}"
        if cache_key in self._field_cache:
            return self._field_cache[cache_key]
        
        try:
            # Get project custom fields with bundle information
            fields = "id,name,fieldType,bundle(id,isUpdateable)"
            response = self.get(f"admin/projects/{project_id}/customFields?fields={fields}")
            self._field_cache[cache_key] = response
            return response
        except Exception as e:
            logger.warning(f"Failed to get custom fields for project {project_id}: {str(e)}")
            return {}
    
    def resolve_field_value(self, field_data: Dict[str, Any], project_id: Optional[str] = None) -> Optional[str]:
        """
        Resolve a custom field value to its human-readable text.
        
        Args:
            field_data: The custom field data from an issue
            project_id: The project ID for context (optional)
            
        Returns:
            Human-readable field value or None if resolution fails
        """
        try:
            field_type = field_data.get("$type", "")
            field_value = field_data.get("value", {})
            field_id = field_data.get("id", "")
            
            # Handle simple values that already have names
            if isinstance(field_value, dict) and "name" in field_value:
                return field_value["name"]
            
            # Handle date fields
            if field_type == "DateIssueCustomField" and isinstance(field_value, (int, float)):
                from datetime import datetime
                try:
                    dt = datetime.fromtimestamp(field_value / 1000)
                    return dt.strftime("%Y-%m-%d")
                except:
                    return str(field_value)
            
            # Handle list values (like multi-user fields)
            if isinstance(field_value, list):
                names = []
                for item in field_value:
                    if isinstance(item, dict) and "name" in item:
                        names.append(item["name"])
                    elif isinstance(item, dict) and "login" in item:
                        names.append(item["login"])
                if names:
                    return ", ".join(names)
                return None
            
            if not isinstance(field_value, dict):
                return None
            
            value_type = field_value.get("$type", "")
            value_id = field_value.get("id", "")
            
            # Try different approaches for state and enum bundles
            if value_type in ["StateBundleElement", "EnumBundleElement"] and project_id and field_id:
                # First, try to get the field definition to find the bundle ID
                try:
                    project_fields = self.get_project_custom_fields(project_id)
                    if isinstance(project_fields, list):
                        for proj_field in project_fields:
                            if proj_field.get("id") == field_id:
                                bundle_id = proj_field.get("bundle", {}).get("id")
                                if bundle_id:
                                    if value_type == "StateBundleElement":
                                        bundle_data = self.get_state_bundle_elements(bundle_id)
                                    else:
                                        bundle_data = self.get_enum_bundle_elements(bundle_id)
                                    
                                    if "values" in bundle_data and isinstance(bundle_data["values"], list):
                                        for value in bundle_data["values"]:
                                            if value.get("id") == value_id:
                                                return value.get("name")
                                break
                except Exception as e:
                    logger.debug(f"Bundle resolution failed for field {field_id}: {str(e)}")
            
            # For State and Priority fields, try common API endpoints
            field_name = field_data.get("name", "").lower()
            if value_type == "StateBundleElement" and "state" in field_name:
                # Try generic state resolution - often states have predictable patterns
                if value_id:
                    # Extract common state names from IDs
                    state_mappings = {
                        "open": "Open",
                        "closed": "Closed", 
                        "resolved": "Resolved",
                        "in-progress": "In Progress",
                        "submitted": "Submitted",
                        "rejected": "Rejected"
                    }
                    for key, name in state_mappings.items():
                        if key in value_id.lower():
                            return name
            
            elif value_type == "EnumBundleElement" and "priority" in field_name:
                # Try generic priority resolution
                if value_id:
                    priority_mappings = {
                        "critical": "Critical",
                        "high": "High",
                        "normal": "Normal", 
                        "low": "Low",
                        "major": "Major",
                        "minor": "Minor"
                    }
                    for key, name in priority_mappings.items():
                        if key in value_id.lower():
                            return name
            
            # Last resort: return the value_id if it looks human-readable
            if value_id and not value_id.startswith(("0-", "1-", "2-", "3-", "4-", "5-", "6-", "7-", "8-", "9-")):
                return value_id
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to resolve field value for field {field_data.get('name', 'unknown')}: {str(e)}")
            return None 