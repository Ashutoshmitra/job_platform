"""
Schema definitions and validation for job data.
"""
from datetime import datetime
from typing import Dict, Any, Tuple, List

TARGET_SCHEMA = {
    "external_job_id": {"type": str, "required": True},
    "job_source": {"type": str, "required": True, "allowed_values": ["COMPANY_WEBSITE", "JOB_FEED"]},
    "feed_id": {"type": int, "required": False, "nullable": True},
    "created_at": {"type": "datetime", "required": True},
    "updated_at": {"type": "datetime", "required": True},
    "posted_at": {"type": "datetime", "required": True},
    "expires_at": {"type": "datetime", "required": False, "nullable": True},
    "status": {"type": str, "required": True},
    "company_name": {"type": str, "required": True},
    "title": {"type": str, "required": True},
    "description": {"type": str, "required": True},
    "application_url": {"type": str, "required": False, "nullable": True},
    "employment_type": {"type": str, "required": False, "nullable": True},
    "is_remote": {"type": bool, "required": True},
    "is_multi_location": {"type": bool, "required": True},
    "is_international": {"type": bool, "required": True},
    "locations": {"type": list, "required": False, "nullable": True},
    "salary_min": {"type": (int, float), "required": False, "nullable": True},
    "salary_max": {"type": (int, float), "required": False, "nullable": True},
    "salary_period": {"type": str, "required": False, "nullable": True},
    "currency": {"type": str, "required": False, "nullable": True},
}

FEED_SCHEMA_MAPPING = {
    # Company Name Mappings
    'company': 'company_name',
    'company_name': 'company_name',
    'companyName': 'company_name',
    'hiring_organization': 'company_name',
    'hiringOrganization': 'company_name',
    'employer': 'company_name',

    # Description Mappings
    'body': 'description',
    'description': 'description',
    'jobDescription': 'description',
    'job_description': 'description',
    'full_description': 'description',
    'details': 'description',
    'job_details': 'description',

    # Posting Date Mappings
    'posted': 'posted_at',
    'date': 'posted_at',
    'posted_at': 'posted_at',
    'datePosted': 'posted_at',
    'date_posted': 'posted_at',
    'publication_date': 'posted_at',
    'post_date': 'posted_at',

    # Application URL Mappings
    'url': 'application_url',
    'job_url': 'application_url',
    'applyLink': 'application_url',
    'application_link': 'application_url',
    'apply_url': 'application_url',
    'link': 'application_url',

    # Job Title Mappings
    'title': 'title',
    'jobTitle': 'title',
    'job_title': 'title',
    'position_title': 'title',
    'position': 'title',
    'role': 'title',

    # Location Mappings
    'location': 'locations',
    'jobLocations': 'locations',
    'job_location': 'locations',
    'address': 'locations',
    'work_location': 'locations',
    'city_state': 'locations',
    'city': 'locations',
    'state': 'locations',
    'country': 'locations',

    # Employment Type Mappings
    'job-type': 'employment_type',
    'job_type': 'employment_type',
    'jobType': 'employment_type',
    'type': 'employment_type',
    'position_type': 'employment_type',
    'contract_type': 'employment_type',
    'employmentType': 'employment_type',

    # External ID Mappings
    'id': 'external_job_id',
    'referencenumber': 'external_job_id',
    'ref_id': 'external_job_id',
    'jobID': 'external_job_id',
    'job_id': 'external_job_id',
    'reference_id': 'external_job_id',
    'requisition_id': 'external_job_id',
    'job_reference': 'external_job_id',

    # Remote Flag Mapping
    'remote': 'is_remote',
    'is_remote': 'is_remote',
    'isRemote': 'is_remote',

    # Salary Mappings
    'salary_min': 'salary_min',
    'min_salary': 'salary_min',
    'minimum_salary': 'salary_min',
    'salary_from': 'salary_min',
    'salary_max': 'salary_max',
    'max_salary': 'salary_max',
    'maximum_salary': 'salary_max',
    'salary_to': 'salary_max',
    'salary_period': 'salary_period',
    'salary_frequency': 'salary_period',
    'pay_period': 'salary_period',
    'currency': 'currency',
    'salary_currency': 'currency',
}


def validate_datetime_string(dt_string: str) -> bool:
    """Checks if a string is a valid ISO 8601 format."""
    try:
        datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False


def transform_job_data(raw_data: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Transforms raw data from a feed into our internal schema format using a mapping.
    """
    transformed_data = {}
    for raw_key, raw_value in raw_data.items():
        target_key = mapping.get(raw_key, raw_key)
        if target_key in TARGET_SCHEMA:
            # Convert data types based on target schema
            if raw_value is not None:
                expected_type = TARGET_SCHEMA[target_key]["type"]
                
                # Convert string booleans
                if target_key in ['is_remote', 'is_multi_location', 'is_international']:
                    if isinstance(raw_value, str):
                        transformed_data[target_key] = raw_value.lower() in ['true', '1', 'yes']
                    else:
                        transformed_data[target_key] = bool(raw_value)
                
                # Convert string numbers for salary fields
                elif target_key in ['salary_min', 'salary_max']:
                    if isinstance(raw_value, str) and raw_value.isdigit():
                        transformed_data[target_key] = int(raw_value)
                    elif isinstance(raw_value, (int, float)):
                        transformed_data[target_key] = raw_value
                    else:
                        transformed_data[target_key] = raw_value
                
                # Handle location field - convert single string to list
                elif target_key == 'locations':
                    if isinstance(raw_value, str):
                        transformed_data[target_key] = [{"location": raw_value.strip()}]
                    elif isinstance(raw_value, list):
                        transformed_data[target_key] = raw_value
                    else:
                        transformed_data[target_key] = raw_value
                
                else:
                    transformed_data[target_key] = raw_value
            else:
                transformed_data[target_key] = raw_value
    
    return transformed_data


def check_schema(job_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates a transformed job data dictionary against the TARGET_SCHEMA.
    """
    errors = []
    
    # Check required fields
    for field, rules in TARGET_SCHEMA.items():
        if rules.get("required") and field not in job_data:
            errors.append(f"Missing required field: '{field}'")
    
    if errors:
        return False, errors

    # Validate field types and values
    for field, value in job_data.items():
        if field in TARGET_SCHEMA:
            rules = TARGET_SCHEMA[field]
            expected_type = rules["type"]
            
            if value is None:
                if not rules.get("nullable"):
                    errors.append(f"Field '{field}' cannot be null.")
                continue
                
            if expected_type == "datetime":
                if not isinstance(value, str) or not validate_datetime_string(value):
                    errors.append(f"Field '{field}' is not a valid ISO datetime string. Got: {value}")
                continue
                
            if not isinstance(value, expected_type):
                errors.append(f"Field '{field}' has incorrect type. Expected {expected_type}, got {type(value)}.")
                
            if "allowed_values" in rules and value not in rules["allowed_values"]:
                errors.append(f"Field '{field}' has value '{value}', but only {rules['allowed_values']} are allowed.")

    # Conditional validation
    if job_data.get("job_source") == "JOB_FEED" and job_data.get("feed_id") is None:
        errors.append("Conditional error: 'feed_id' is required when 'job_source' is 'JOB_FEED'.")
    if job_data.get("job_source") == "COMPANY_WEBSITE" and job_data.get("feed_id") is not None:
        errors.append("Conditional error: 'feed_id' must be null when 'job_source' is 'COMPANY_WEBSITE'.")

    return not errors, errors