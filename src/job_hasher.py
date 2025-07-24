"""
Job hashing utilities for deduplication.
"""
import json
import base64
import hashlib
from typing import Dict, Any


def get_canonical_job_hash(job_data: Dict[str, Any]) -> str:
    """
    Creates a unique and stable Base64 hash for a job object by focusing
    on its core, location-independent content.

    This function ignores variations in external IDs, locations, and application URLs
    to identify true duplicates.

    Args:
        job_data (dict): The job data dictionary.

    Returns:
        str: A unique Base64 encoded SHA256 hash representing the job's core content.
    """
    # Define the core fields that truly determine the uniqueness of a job,
    # independent of its location or source-specific IDs.
    uniqueness_fields = [
        'company_name',
        'title',
        'description',
        'employment_type',
    ]

    # Create a dictionary with only the core fields.
    canonical_dict = {key: job_data.get(key) for key in uniqueness_fields}

    # Create a stable, sorted JSON string.
    canonical_string = json.dumps(canonical_dict, sort_keys=True, separators=(',', ':'))

    # Hash the string using SHA256 for a secure, fixed-length output.
    hash_object = hashlib.sha256(canonical_string.encode('utf-8'))

    # Encode the binary hash in Base64 for easy storage and comparison.
    base64_hash = base64.b64encode(hash_object.digest()).decode('utf-8')

    return base64_hash