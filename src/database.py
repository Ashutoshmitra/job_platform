"""
Database operations for Supabase integration.
"""
import logging
from typing import Dict, Any, List, Set, Optional
from supabase import create_client, Client
from .config import Config

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for database operations."""
    
    def __init__(self):
        """Initialize the Supabase client."""
        self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    
    def get_existing_job_hashes(self) -> Set[str]:
        """
        Get all existing job hashes from the database.
        
        Returns:
            Set[str]: Set of existing job hashes.
        """
        try:
            response = self.client.table("open_jobs").select("job_hash").execute()
            return {job['job_hash'] for job in response.data if job.get('job_hash')}
        except Exception as e:
            logger.error(f"Error fetching existing job hashes: {e}")
            return set()
    
    def get_active_job_hashes(self) -> Dict[str, int]:
        """
        Get all active job hashes and their IDs from the database.
        
        Returns:
            Dict[str, int]: Dictionary mapping job hashes to job IDs.
        """
        try:
            response = self.client.table("open_jobs").select("id,job_hash").eq("status", "ACTIVE").execute()
            return {job['job_hash']: job['id'] for job in response.data if job.get('job_hash')}
        except Exception as e:
            logger.error(f"Error fetching active job hashes: {e}")
            return {}
    
    def insert_job(self, job_data: Dict[str, Any]) -> bool:
        """
        Insert a new job into the database.
        
        Args:
            job_data: The job data to insert.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            response = self.client.table("open_jobs").insert(job_data).execute()
            if response.data:
                logger.info(f"Successfully inserted job: {job_data.get('external_job_id')}")
                return True
            else:
                logger.error("Failed to insert job - no data returned")
                return False
        except Exception as e:
            logger.error(f"Error inserting job {job_data.get('external_job_id')}: {e}")
            return False
    
    def close_jobs_by_hashes(self, job_hashes: List[str]) -> int:
        """
        Mark jobs as closed by their hashes.
        
        Args:
            job_hashes: List of job hashes to close.
            
        Returns:
            int: Number of jobs closed.
        """
        if not job_hashes:
            return 0
            
        try:
            response = self.client.table("open_jobs")\
                .update({"status": "CLOSED"})\
                .in_("job_hash", job_hashes)\
                .execute()
            
            closed_count = len(response.data) if response.data else 0
            logger.info(f"Closed {closed_count} jobs")
            return closed_count
        except Exception as e:
            logger.error(f"Error closing jobs: {e}")
            return 0
    
    def extract_and_load_job(self, job_data: Dict[str, Any], table_name: str = "open_jobs") -> bool:
        """
        Validate job data and load it into the database.
        
        Args:
            job_data: The job data to validate and insert.
            table_name: The table name to insert into.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        from .schema import check_schema, TARGET_SCHEMA
        
        logger.info(f"Processing job with external_id: {job_data.get('external_job_id', 'N/A')}")
        
        # Validate the data against the schema
        is_valid, errors = check_schema(job_data)
        
        if not is_valid:
            logger.error(f"Validation FAILED. Errors: {errors}")
            return False
        
        logger.info("Validation PASSED.")
        
        # Extract only the fields defined in our schema
        extracted_data = {key: job_data[key] for key in TARGET_SCHEMA if key in job_data}
        
        return self.insert_job(extracted_data)