"""
AI service for job enrichment using Gemini API.
"""
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from .config import Config

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered job enrichment."""
    
    def __init__(self):
        """Initialize the Gemini client."""
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self._industry_cache = {}
        self._industry_batch = []
        self._batch_limit = 5
    
    def add_job_for_industry_classification(self, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a job to the batch for industry classification."""
        job_key = (job.get('title'), job.get('description'))
        if job_key in self._industry_cache:
            logger.info(f"Industry cache hit for job title: {job.get('title')}")
            return self._industry_cache[job_key]
        
        self._industry_batch.append(job)
        logger.info(f"Added job '{job.get('title')}' to industry batch. Current batch size: {len(self._industry_batch)}")
        return None
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response text to JSON, handling potential formatting issues."""
        try:
            # Try to parse as JSON directly
            parsed = json.loads(response_text)
            # Ensure it's a dictionary
            if isinstance(parsed, dict):
                return parsed
            else:
                logger.warning(f"Parsed JSON is not a dict: {type(parsed)}")
                return {}
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if '```json' in response_text:
                start = response_text.find('```json') + 7
                end = response_text.find('```', start)
                if end != -1:
                    json_text = response_text[start:end].strip()
                    try:
                        parsed = json.loads(json_text)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass
            
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass
            
            logger.error(f"Could not parse AI response as valid JSON dict: {response_text[:200]}...")
            return {}
    
    async def process_industry_batch(self) -> None:
        """Process the current batch of jobs for industry classification."""
        if not self._industry_batch:
            logger.info("Industry batch is empty. Nothing to process.")
            return
        
        logger.info(f"Processing an industry batch of {len(self._industry_batch)} jobs")
        
        # Create a single prompt for the entire batch
        prompt_lines = [
            "Analyze the following job listings and return a JSON object for each with sector, industry_group, industry, and industry_id fields.",
            "Format: {\"sector\": \"Technology\", \"industry_group\": \"Software & IT Services\", \"industry\": \"Software\", \"industry_id\": 501}",
            "---"
        ]
        
        for i, job in enumerate(self._industry_batch):
            prompt_lines.append(f"Job {i+1}:")
            prompt_lines.append(f"Title: {job.get('title', '')}")
            prompt_lines.append(f"Description: {job.get('description', '')[:500]}...")  # Limit description length
            prompt_lines.append("---")
        
        prompt = "\n".join(prompt_lines)
        
        try:
            response = await self._generate_content_async(prompt, timeout=15)
            classification = self._parse_ai_response(response.text)
            
            # Ensure classification is a dictionary
            if not isinstance(classification, dict):
                logger.warning(f"Classification is not a dict, got: {type(classification)}. Using default.")
                raise ValueError("Classification response is not a dictionary")
            
            # Apply classification to all jobs in batch
            for job in self._industry_batch:
                job.update(classification)
                job_key = (job.get('title'), job.get('description'))
                self._industry_cache[job_key] = classification
                logger.info(f"Enriched job '{job.get('title')}' with industry info.")
            
        except Exception as e:
            logger.error(f"Error processing industry batch: {e}")
            logger.error(f"Raw response was: {response.text if 'response' in locals() else 'No response'}")
            # Add default classification for failed jobs
            default_classification = {
                "sector": "Unknown",
                "industry_group": "Unknown",
                "industry": "Unknown",
                "industry_id": 999
            }
            for job in self._industry_batch:
                job.update(default_classification)
        
        # Clear the batch after processing
        self._industry_batch.clear()
        logger.info("Industry batch processing complete.")
    
    async def _generate_content_async(self, prompt: str, timeout: int = 10):
        """Generate content using Gemini API asynchronously with timeout."""
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, self.model.generate_content, prompt),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Gemini API request timed out after {timeout} seconds")
            raise Exception(f"AI service timeout after {timeout} seconds")
    
    async def generate_ai_attributes(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered attributes for a single job posting.
        
        Args:
            job_data: The job dictionary, ideally already enriched with industry info.
            
        Returns:
            dict: The job dictionary updated with ai_ prefixed fields.
        """
        logger.info(f"Generating AI attributes for job: {job_data.get('title')}")
        
        prompt = f"""
        Based on the following job data, generate a structured JSON object containing these fields:
        - ai_title: Improved, standardized job title
        - ai_description: Clean, professional job description (2-3 sentences)
        - ai_job_tasks: Array of 3-5 key job responsibilities
        - ai_search_terms: Array of relevant search keywords
        - ai_top_tags: Array of 3-5 most important skills/technologies
        - ai_job_function_id: Numeric ID representing job function (100-999)
        - ai_skills: Array of specific skills required
        - ai_confidence_score: Float between 0.0 and 1.0 indicating parsing confidence

        Job Data:
        - Title: {job_data.get('title', '')}
        - Company: {job_data.get('company_name', '')}
        - Description: {job_data.get('description', '')[:1000]}...
        - Industry: {job_data.get('industry', 'N/A')}

        Return only valid JSON format.
        """
        
        try:
            response = await self._generate_content_async(prompt, timeout=15)
            ai_data = self._parse_ai_response(response.text)
            
            # Ensure confidence score is valid
            if 'ai_confidence_score' not in ai_data or not isinstance(ai_data['ai_confidence_score'], (int, float)):
                ai_data['ai_confidence_score'] = 0.75  # Default confidence
            
            job_data.update(ai_data)
            logger.info("Successfully enriched job with AI attributes.")
            return job_data
            
        except Exception as e:
            logger.error(f"Error generating AI attributes: {e}")
            # Add default AI attributes
            default_ai_data = {
                "ai_title": job_data.get('title', 'Unknown Position'),
                "ai_description": job_data.get('description', 'No description available')[:200] + "...",
                "ai_job_tasks": ["Review job posting for details"],
                "ai_search_terms": ["general"],
                "ai_top_tags": ["General"],
                "ai_job_function_id": 999,
                "ai_skills": ["To be determined"],
                "ai_confidence_score": 0.3
            }
            job_data.update(default_ai_data)
            return job_data