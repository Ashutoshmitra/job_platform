# Job Data Ingestion & Enrichment Pipeline

An automated ETL pipeline that processes job feeds, validates and transforms data, enriches with AI-powered attributes, detects duplicates, and routes jobs based on confidence scores for automatic approval or manual review.

## Features

### 🔄 **Complete ETL Pipeline**
- **Extract**: Process job feeds from URLs (XML, CSV, JSON)
- **Transform**: Schema mapping and data validation 
- **Load**: Store validated jobs in Supabase database

### 🤖 **AI-Powered Enrichment**
- Industry classification using Deepseek API
- Generate enhanced job attributes (ai_title, ai_description, ai_skills, etc.)
- Confidence scoring for job quality assessment

### 🎯 **Smart Job Management**
- **Duplicate Detection**: Content-based hashing prevents duplicate job entries
- **Job Lifecycle**: Automatically close jobs no longer in feeds
- **Confidence Routing**: Auto-approve high-confidence jobs (≥0.86), queue low-confidence for review

### 🔗 **External Integrations**
- **Supabase**: Job data storage and management
- **Xano**: Auto-approved jobs synced to external platform
- **Deepseek AI**: Industry classification and job enrichment

## Architecture

```
Job Feed URL → File Processing → Schema Validation → Duplicate Check → AI Enrichment → Confidence Check
                                                                                           ↓
Manual Review Queue ←← Low Confidence (<0.86) ←←←←←←←←←←←←← OR ←←←←→→ High Confidence (≥0.86) → Xano Sync
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and service status |
| `/process` | POST | Process job feed from URL |
| `/status` | GET | Pipeline status and configuration |
| `/queue` | GET | Manual review queue contents |

## Usage

### Process a Job Feed
```bash
curl -X POST https://job-platform-uxbj.onrender.com/process \
  -H "Content-Type: application/json" \
  -d '{"input_path": "https://example.com/jobs.xml"}'
```

### Check Review Queue
```bash
curl https://job-platform-uxbj.onrender.com/queue
```

## Configuration

Set these environment variables:

```bash
# Database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# AI Service  
DEEPSEEK_API_KEY=your_deepseek_api_key

# External Platform
XANO_API_URL=your_xano_api_url
XANO_API_KEY=your_xano_api_key

# Pipeline Settings
CONFIDENCE_THRESHOLD=0.86
PORT=8080
```

## Supported File Formats

- **XML**: Job feeds in XML format
- **CSV**: Comma-separated job data
- **JSON**: JSON-formatted job listings
- **Archives**: ZIP, TAR.GZ, TGZ compressed files

## Data Flow

1. **Input Processing**: Download and parse job feed files
2. **Schema Mapping**: Transform various feed formats to internal schema
3. **Validation**: Ensure required fields and data types
4. **Duplicate Detection**: Generate content hash and check against existing jobs
5. **Job Lifecycle**: Close jobs no longer present in feeds
6. **AI Enrichment**: 
   - Batch industry classification
   - Generate AI-enhanced job attributes
   - Calculate confidence scores
7. **Routing**:
   - High confidence (≥0.86): Auto-sync to Xano
   - Low confidence (<0.86): Add to manual review queue

## Schema Mapping

The pipeline handles various feed formats by mapping common field names:

```python
# Examples of supported field mappings
'company' → 'company_name'
'jobTitle' → 'title'  
'requisition_id' → 'external_job_id'
'datePosted' → 'posted_at'
'isRemote' → 'is_remote'
```

## Deployment

The application is containerized and deployed on Render:

```dockerfile
# Build and run
docker build -t job-platform .
docker run -p 8080:8080 job-platform
```

## Monitoring

- **Health Check**: `/health` endpoint for service monitoring
- **Status Info**: `/status` shows pipeline configuration and queue status
- **Logging**: Comprehensive logging for debugging and monitoring

## Live Application

🌐 **Production URL**: https://job-platform-uxbj.onrender.com

Test the pipeline:
```bash
curl -X POST https://job-platform-uxbj.onrender.com/process \
  -H "Content-Type: application/json" \
  -d '{"input_path": "https://raw.githubusercontent.com/Ashutoshmitra/job_platform/main/test_deploy.xml"}'
```