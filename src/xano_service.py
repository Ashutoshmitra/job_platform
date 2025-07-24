"""
Xano service for job data synchronization.
"""
import json
import logging
import requests
from typing import Dict, Any
from .config import Config

logger = logging.getLogger(__name__)


class XanoService:
    """Service for Xano database operations."""
    
    def __init__(self):
        """Initialize the Xano service."""
        self.api_url = Config.XANO_API_URL
        self.api_key = Config.XANO_API_KEY
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def sync_to_xano(self, job_data: Dict[str, Any]) -> bool:
        """
        Sync a validated and approved job object to Xano database.
        
        Args:
            job_data: The job data to be uploaded.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        logger.info(f"Auto-approving and syncing job: '{job_data.get('ai_title', job_data.get('title'))}'")
        
        # Remove confidence score before syncing
        job_copy = job_data.copy()
        job_copy.pop('ai_confidence_score', None)
        
        try:
            # The endpoint for your jobs table in Xano
            jobs_endpoint = f"{self.api_url}/job_platform"
            response = requests.post(
                jobs_endpoint, 
                headers=self.headers,
                json=job_copy,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                logger.info(f"Successfully synced job to Xano. Record ID: {response_data.get('id', 'Unknown')}")
                return True
            else:
                logger.error(f"Failed to sync job to Xano. Status: {response.status_code}, Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during Xano sync: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Xano sync: {e}")
            return False