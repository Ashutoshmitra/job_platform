"""
Configuration management for the Job Data Ingestion Pipeline.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration."""
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    # Gemini AI Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Xano Configuration
    XANO_API_URL = os.getenv('XANO_API_URL')
    XANO_API_KEY = os.getenv('XANO_API_KEY')
    
    # Application Configuration
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.86'))
    PORT = int(os.getenv('PORT', '8080'))
    
    # Validation
    @classmethod
    def validate(cls):
        """Validate that all required environment variables are set."""
        required_vars = [
            'SUPABASE_URL', 'SUPABASE_KEY', 'GEMINI_API_KEY',
            'XANO_API_URL', 'XANO_API_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True