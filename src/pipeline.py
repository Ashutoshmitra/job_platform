"""
Main ETL pipeline orchestration.
"""
import asyncio
import logging
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, List, Set
from .config import Config
from .file_processor import process_input
from .schema import transform_job_data, FEED_SCHEMA_MAPPING
from .job_hasher import get_canonical_job_hash
from .database import DatabaseService
from .ai_service import AIService
from .xano_service import XanoService
from .review_queue import ReviewQueue

logger = logging.getLogger(__name__)


class JobPipeline:
    """Main ETL pipeline for job data processing."""
    
    def __init__(self):
        """Initialize the pipeline with all services."""
        self.db_service = DatabaseService()
        self.ai_service = AIService()
        self.xano_service = XanoService()
        self.review_queue = ReviewQueue()
        self.confidence_threshold = Config.CONFIDENCE_THRESHOLD
    
    def check_confidence_and_route(self, job: Dict[str, Any]) -> bool:
        """
        Check the AI confidence score and route for auto-approval or manual review.
        
        Args:
            job: The enriched job data dictionary.
            
        Returns:
            bool: True if processed successfully, False otherwise.
        """
        job_title = job.get('ai_title', job.get('title', 'N/A'))
        confidence_score = job.get('ai_confidence_score')
        
        logger.info(f"Processing job: '{job_title}' with confidence: {confidence_score}")
        
        if confidence_score is None:
            logger.warning(f"Confidence score not found for {job_title}. Defaulting to manual review.")
            return self.review_queue.send_for_manual_review(job)
        
        if confidence_score >= self.confidence_threshold:
            logger.info(f"Confidence {confidence_score} >= {self.confidence_threshold}. Auto-approving.")
            return self.xano_service.sync_to_xano(job)
        else:
            logger.info(f"Confidence {confidence_score} < {self.confidence_threshold}. Sending for manual review.")
            return self.review_queue.send_for_manual_review(job)
    
    def check_and_close_jobs(self, new_feed_jobs: List[Dict[str, Any]]) -> int:
        """
        Compare new job feed against database to identify and close inactive jobs.
        
        Args:
            new_feed_jobs: List of job dictionaries from the new feed.
            
        Returns:
            int: Number of jobs closed.
        """
        logger.info("Starting job closure check")
        
        # Get all job hashes from the new feed
        hashes_in_new_feed = {get_canonical_job_hash(job) for job in new_feed_jobs}
        logger.info(f"Found {len(hashes_in_new_feed)} unique job hashes in the new feed")
        
        # Get all active job hashes currently in the database
        active_jobs_in_db = self.db_service.get_active_job_hashes()
        logger.info(f"Found {len(active_jobs_in_db)} active job hashes in the database")
        
        # Find hashes that are in DB but not in new feed
        hashes_to_close = set(active_jobs_in_db.keys()) - hashes_in_new_feed
        
        if not hashes_to_close:
            logger.info("No jobs to close. All active jobs in DB are present in the new feed.")
            return 0
        
        logger.info(f"Found {len(hashes_to_close)} jobs to mark as CLOSED")
        return self.db_service.close_jobs_by_hashes(list(hashes_to_close))
    
    def process_and_insert_jobs(self, new_jobs: List[Dict[str, Any]]) -> int:
        """
        Process a list of new jobs, check for duplicates, and insert unique ones.
        
        Args:
            new_jobs: List of new job dictionaries to process.
            
        Returns:
            int: Number of new jobs inserted.
        """
        logger.info("Starting duplicate job check and insertion")
        
        # Get all existing job hashes from database
        existing_hashes = self.db_service.get_existing_job_hashes()
        logger.info(f"Found {len(existing_hashes)} existing job hashes in the database")
        
        new_jobs_inserted = 0
        for job in new_jobs:
            job_hash = get_canonical_job_hash(job)
            job_title = job.get('title', 'N/A')
            
            logger.info(f"Processing job '{job_title}' | Hash: {job_hash[:10]}...")
            
            if job_hash in existing_hashes:
                logger.info("Result: DUPLICATE. Job already exists in database. Skipping.")
            else:
                logger.info("Result: UNIQUE. Inserting new job.")
                
                # Add hash to job data and metadata
                job_to_insert = job.copy()
                job_to_insert['job_hash'] = job_hash
                job_to_insert['job_source'] = 'JOB_FEED'
                job_to_insert['feed_id'] = 1  # Could be parameterized
                job_to_insert['status'] = 'ACTIVE'
                job_to_insert['created_at'] = datetime.utcnow().isoformat() + 'Z'
                job_to_insert['updated_at'] = datetime.utcnow().isoformat() + 'Z'
                
                # Set default boolean values if not present
                job_to_insert.setdefault('is_remote', False)
                job_to_insert.setdefault('is_multi_location', False)
                job_to_insert.setdefault('is_international', False)
                
                if self.db_service.extract_and_load_job(job_to_insert):
                    existing_hashes.add(job_hash)
                    new_jobs_inserted += 1
        
        logger.info(f"Process complete. Inserted {new_jobs_inserted} new jobs.")
        return new_jobs_inserted
    
    async def enrich_jobs_with_ai(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich jobs with AI-generated attributes.
        
        Args:
            jobs: List of job dictionaries to enrich.
            
        Returns:
            List of enriched job dictionaries.
        """
        logger.info(f"Starting AI enrichment for {len(jobs)} jobs")
        
        # Step 1: Classify industries in batch
        for job in jobs:
            self.ai_service.add_job_for_industry_classification(job)
        
        await self.ai_service.process_industry_batch()
        
        # Step 2: Generate AI attributes for each job
        enriched_jobs = []
        for job in jobs:
            try:
                enriched_job = await self.ai_service.generate_ai_attributes(job)
                enriched_jobs.append(enriched_job)
            except Exception as e:
                logger.error(f"Error enriching job {job.get('title', 'Unknown')}: {e}")
                enriched_jobs.append(job)  # Add without enrichment
        
        logger.info(f"AI enrichment complete for {len(enriched_jobs)} jobs")
        return enriched_jobs
    
    async def process_feed(self, input_path: str) -> Dict[str, Any]:
        """
        Process a complete job feed through the entire pipeline.
        
        Args:
            input_path: Path or URL to the job feed data.
            
        Returns:
            Dict containing processing results and statistics.
        """
        results = {
            "success": False,
            "input_path": input_path,
            "jobs_processed": 0,
            "jobs_inserted": 0,
            "jobs_closed": 0,
            "jobs_auto_approved": 0,
            "jobs_manual_review": 0,
            "errors": []
        }
        
        try:
            # Create temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info(f"Starting pipeline processing for: {input_path}")
                
                # Step 1: Process input (download, extract, parse)
                logger.info("Step 1: Processing input files")
                parsed_data = process_input(input_path, temp_dir)
                
                if not parsed_data:
                    results["errors"].append("No data could be parsed from input")
                    return results
                
                # Step 2: Transform and validate job data
                logger.info("Step 2: Transforming and validating job data")
                all_jobs = []
                for filename, data in parsed_data.items():
                    jobs_to_process = []
                    
                    # Handle nested XML structure like {"jobs": {"job": [...]}}
                    if isinstance(data, dict):
                        # Check for common job list patterns
                        if 'jobs' in data and isinstance(data['jobs'], dict):
                            if 'job' in data['jobs']:
                                job_data = data['jobs']['job']
                                if isinstance(job_data, list):
                                    jobs_to_process.extend(job_data)
                                elif isinstance(job_data, dict):
                                    jobs_to_process.append(job_data)
                        # Check if data itself contains job fields
                        elif any(key in data for key in ['title', 'company', 'company_name', 'external_job_id', 'id']):
                            jobs_to_process.append(data)
                        # Handle other nested structures
                        else:
                            for key, value in data.items():
                                if isinstance(value, list):
                                    jobs_to_process.extend(value)
                                elif isinstance(value, dict):
                                    jobs_to_process.append(value)
                    elif isinstance(data, list):
                        jobs_to_process.extend(data)
                    
                    # Transform each job
                    for job_item in jobs_to_process:
                        if isinstance(job_item, dict):
                            transformed_job = transform_job_data(job_item, FEED_SCHEMA_MAPPING)
                            if transformed_job and any(key in transformed_job for key in ['title', 'company_name', 'external_job_id']):
                                all_jobs.append(transformed_job)
                
                results["jobs_processed"] = len(all_jobs)
                logger.info(f"Processed {len(all_jobs)} jobs from feed")
                
                if not all_jobs:
                    results["errors"].append("No valid jobs found after transformation")
                    return results
                
                # Step 3: Check for closed jobs
                logger.info("Step 3: Checking for jobs to close")
                results["jobs_closed"] = self.check_and_close_jobs(all_jobs)
                
                # Step 4: Insert new unique jobs
                logger.info("Step 4: Inserting unique jobs")
                results["jobs_inserted"] = self.process_and_insert_jobs(all_jobs)
                
                # Step 5: AI enrichment for new jobs
                if results["jobs_inserted"] > 0:
                    logger.info("Step 5: AI enrichment")
                    enriched_jobs = await self.enrich_jobs_with_ai(all_jobs[:results["jobs_inserted"]])
                    
                    # Step 6: Route based on confidence
                    logger.info("Step 6: Confidence-based routing")
                    for job in enriched_jobs:
                        try:
                            confidence = job.get('ai_confidence_score', 0)
                            if self.check_confidence_and_route(job):
                                if confidence >= self.confidence_threshold:
                                    results["jobs_auto_approved"] += 1
                                else:
                                    results["jobs_manual_review"] += 1
                        except Exception as e:
                            logger.error(f"Error routing job {job.get('title', 'Unknown')}: {e}")
                            results["errors"].append(f"Routing error: {str(e)}")
                
                results["success"] = True
                logger.info("Pipeline processing completed successfully")
                
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            results["errors"].append(str(e))
        
        return results