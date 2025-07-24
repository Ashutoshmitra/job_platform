# Job Data Ingestion & Enrichment Pipeline

A production-ready ETL pipeline that automates the ingestion, transformation, validation, AI enrichment, and distribution of job posting data from various sources.

## 🏗️ Architecture Overview

This pipeline processes job data through the following stages:

1. **INTAKE**: File detection, URL/path parsing, archive extraction
2. **UNZIP**: Handles ZIP, TAR.GZ, TGZ, GZ archives  
3. **PARSE**: Converts CSV, JSON, XML, INI to standardized JSON
4. **SCHEMA CHECK**: Validates against target job schema with field mapping
5. **EXTRACTION**: Database integration with deduplication
6. **AI ENRICHMENT**: Gemini API integration for job enhancement
7. **CONFIDENCE ROUTING**: Auto-approval vs manual review logic
8. **AUTO-APPROVAL**: High-confidence jobs go to Xano
9. **MANUAL REVIEW**: Low-confidence jobs queued for review

```
[Data Sources] → [File Processing] → [Schema Validation] → [Deduplication]
       ↓
[AI Enrichment] → [Confidence Check] → [Auto-Approve | Manual Review]
       ↓                    ↓                     ↓
   [Xano DB]           [Review Queue]        [Analytics]
```

## 🚀 Quick Start

### Prerequisites

- Docker installed
- Google Cloud SDK installed and configured
- API credentials for:
  - Supabase (database)
  - Google Gemini (AI enrichment)
  - Xano (final data destination)

### Local Development

1. **Clone and setup environment:**
```bash
git clone <repository-url>
cd upwork2407
cp .env.example .env
# Edit .env with your API credentials
```

2. **Install dependencies:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Run locally:**
```bash
# Use the virtual environment Python directly due to shell aliases
./venv/bin/python app.py
```

4. **Test the application:**
```bash
curl http://localhost:8080/health
```

### Docker Development

1. **Build the container:**
```bash
docker build -t job-pipeline .
```

2. **Run the container:**
```bash
docker run -p 8080:8080 --env-file .env job-pipeline
```

## 🌩️ Google Cloud Run Deployment

### One-Command Deployment

1. **Set environment variables:**
```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_REGION=us-central1  # Optional, defaults to us-central1
```

2. **Deploy:**
```bash
./deploy.sh
```

3. **Set API credentials:**
```bash
./set-env-vars.sh
```

### Manual Deployment

1. **Build and push image:**
```bash
docker build -t gcr.io/your-project-id/job-pipeline .
docker push gcr.io/your-project-id/job-pipeline
```

2. **Deploy to Cloud Run:**
```bash
gcloud run deploy job-pipeline \
    --image gcr.io/your-project-id/job-pipeline \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 1 \
    --timeout 300
```

3. **Set environment variables:**
```bash
gcloud run services update job-pipeline --region=us-central1 \
    --set-env-vars=\"SUPABASE_URL=...,SUPABASE_KEY=...,GEMINI_API_KEY=...,XANO_API_URL=...,XANO_API_KEY=...\"
```

## 📡 API Endpoints

### Health Check
```bash
GET /health
```
Returns service health status and version information.

### Process Job Feed
```bash
POST /process
Content-Type: application/json

{
    "input_path": "https://example.com/jobs.xml"
}
```

Processes a complete job feed through the entire pipeline. Supports:
- **URLs**: HTTP/HTTPS URLs to job feeds
- **Local files**: File paths for local processing
- **Multiple formats**: XML, JSON, CSV, ZIP archives

**Response:**
```json
{
    "success": true,
    "input_path": "https://example.com/jobs.xml",
    "jobs_processed": 150,
    "jobs_inserted": 45,
    "jobs_closed": 12,
    "jobs_auto_approved": 38,
    "jobs_manual_review": 7,
    "errors": []
}
```

### Pipeline Status
```bash
GET /status
```
Returns current pipeline configuration and review queue status.

### Review Queue
```bash
GET /queue
```
Returns all jobs currently in the manual review queue.

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_KEY` | Yes | Supabase API key |
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `XANO_API_URL` | Yes | Xano API endpoint URL |
| `XANO_API_KEY` | Yes | Xano API key |
| `CONFIDENCE_THRESHOLD` | No | AI confidence threshold (default: 0.86) |
| `PORT` | No | Application port (default: 8080) |

### Job Schema

The pipeline validates all jobs against a comprehensive schema:

```python
{
    "external_job_id": str,      # Required: Unique identifier from source
    "job_source": str,           # Required: "COMPANY_WEBSITE" | "JOB_FEED"
    "company_name": str,         # Required: Company name
    "title": str,                # Required: Job title
    "description": str,          # Required: Job description
    "posted_at": datetime,       # Required: ISO 8601 datetime
    "status": str,              # Required: Job status
    "is_remote": bool,          # Required: Remote work flag
    "application_url": str,     # Optional: Apply URL
    "employment_type": str,     # Optional: Full-time, part-time, etc.
    "locations": list,          # Optional: Job locations
    "salary_min": int/float,    # Optional: Minimum salary
    "salary_max": int/float,    # Optional: Maximum salary
    # ... additional fields
}
```

## 🤖 AI Enrichment

The pipeline uses Google Gemini to enhance job data with:

- **AI Title**: Standardized, professional job titles
- **AI Description**: Clean, structured job descriptions
- **AI Skills**: Extracted required skills and technologies
- **AI Tasks**: Key job responsibilities
- **AI Search Terms**: Relevant keywords for discoverability
- **Industry Classification**: Sector, industry group, and industry codes
- **Confidence Score**: AI assessment of data quality (0.0-1.0)

Jobs with confidence scores ≥ threshold are auto-approved to Xano. Lower confidence jobs are queued for manual review.

## 📊 Data Flow

### Supported Input Formats

- **XML**: Job feeds in XML format
- **JSON**: Structured job data
- **CSV**: Tabular job listings
- **Archives**: ZIP, TAR.GZ, TGZ files containing job data

### Field Mapping

The pipeline automatically maps common field variations to the standard schema:

```python
{
    'company': 'company_name',
    'companyName': 'company_name',
    'hiring_organization': 'company_name',
    'jobTitle': 'title',
    'position_title': 'title',
    'description': 'description',
    'job_details': 'description',
    'datePosted': 'posted_at',
    'publication_date': 'posted_at',
    # ... 50+ field mappings
}
```

### Deduplication

Jobs are deduplicated using a hash of core content (company, title, description, employment type), ignoring location and ID variations to catch true duplicates across sources.

## 🧪 Testing

### Unit Tests
```bash
# Run with mock services
./venv/bin/python test_app.py
```

### Integration Tests
```bash
# Test with sample data
curl -X POST http://localhost:8080/process \
    -H "Content-Type: application/json" \
    -d '{"input_path": "test_data.json"}'
```

### Cloud Run Testing
```bash
# Health check
curl https://your-service-url/health

# Process sample feed
curl -X POST https://your-service-url/process \
    -H "Content-Type: application/json" \
    -d '{"input_path": "https://example.com/jobs.xml"}'
```

## 📁 Project Structure

```
upwork2407/
├── app.py                 # Flask application entry point
├── Dockerfile            # Container configuration
├── requirements.txt      # Python dependencies
├── deploy.sh            # Cloud Run deployment script
├── set-env-vars.sh      # Environment configuration script
├── src/                 # Application source code
│   ├── config.py        # Configuration management
│   ├── pipeline.py      # Main ETL orchestration
│   ├── file_processor.py # File handling and parsing
│   ├── schema.py        # Data validation and transformation
│   ├── database.py      # Supabase integration
│   ├── ai_service.py    # Gemini AI integration
│   ├── xano_service.py  # Xano API integration
│   ├── review_queue.py  # Manual review queue
│   ├── job_hasher.py    # Deduplication logic
│   └── mock_services.py # Testing utilities
├── test_app.py          # Application tests
├── test_data.json       # Sample test data
└── README.md           # This documentation
```

## 🚨 Error Handling

The pipeline includes comprehensive error handling:

- **Validation Errors**: Jobs failing schema validation are logged and skipped
- **Network Errors**: Retry logic for API calls with exponential backoff
- **Processing Errors**: Individual job failures don't stop batch processing
- **Resource Limits**: Cloud Run timeout and memory management

## 📈 Monitoring

Monitor your pipeline using:

- **Cloud Run Metrics**: Request count, latency, error rates
- **Application Logs**: Structured logging with request tracing  
- **Review Queue**: Manual oversight for low-confidence jobs
- **Health Endpoint**: Service availability monitoring

## 🔒 Security

- **API Keys**: Stored as environment variables, never in code
- **HTTPS**: All external communications encrypted
- **Input Validation**: All inputs validated and sanitized
- **Resource Limits**: Container resource constraints prevent abuse

## 📞 Support

For issues or questions:

1. Check the application logs in Cloud Run console
2. Test with the `/health` endpoint
3. Verify environment variables are set correctly
4. Review the manual review queue for processing issues

## 🎯 Performance

- **Batch Processing**: Industry classification processed in batches
- **Async Operations**: AI enrichment runs asynchronously
- **Caching**: Industry classification results cached
- **Resource Efficiency**: Optimized for Cloud Run's serverless model

**Typical Performance:**
- 100 jobs: ~2-3 minutes
- 1000 jobs: ~15-20 minutes
- Memory usage: ~500MB-1GB
- Cold start: ~5 seconds

---

**🎉 Your Job Data Ingestion Pipeline is ready for production!**