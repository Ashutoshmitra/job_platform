# Testing Guide

## 🧪 How to Test the Job Data Ingestion Pipeline

This guide provides step-by-step instructions for testing the pipeline at different stages.

## 📁 Clean Project Structure

After cleanup, your project should contain only these essential files:

```
upwork2407/
├── app.py                 # Flask application entry point
├── Dockerfile            # Container configuration
├── requirements.txt      # Python dependencies
├── deploy.sh            # Cloud Run deployment script
├── set-env-vars.sh      # Environment configuration script
├── .env.example         # Environment variables template
├── .env                 # Your environment variables (local testing)
├── .gitignore           # Git ignore patterns
├── .dockerignore        # Docker ignore patterns
├── src/                 # Application source code
│   ├── __init__.py      # Python package marker
│   ├── config.py        # Configuration management
│   ├── pipeline.py      # Main ETL orchestration
│   ├── file_processor.py # File handling and parsing
│   ├── schema.py        # Data validation and transformation
│   ├── database.py      # Supabase integration
│   ├── ai_service.py    # Gemini AI integration
│   ├── xano_service.py  # Xano API integration
│   ├── review_queue.py  # Manual review queue
│   ├── job_hasher.py    # Deduplication logic
│   └── mock_services.py # Testing utilities (optional in production)
├── test_data.json       # Sample test data
├── README.md           # Complete documentation
├── DEPLOYMENT_SUMMARY.md # Project completion summary
└── TESTING_GUIDE.md    # This file
```

## 🚀 Testing Options

### Option 1: Local Development Testing (Recommended)

**Step 1: Setup Environment**
```bash
# Clone/navigate to project
cd upwork2407

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Step 2: Configure Environment Variables**
```bash
# Copy and edit environment file
cp .env.example .env

# Edit .env with your real API credentials
# Required variables:
# SUPABASE_URL=your_supabase_url
# SUPABASE_KEY=your_supabase_key  
# GEMINI_API_KEY=your_gemini_key
# XANO_API_URL=your_xano_url
# XANO_API_KEY=your_xano_key
```

**Step 3: Run Application**
```bash
# Start the application (use direct path to avoid shell aliases)
./venv/bin/python app.py

# Or if the above doesn't work:
python3 app.py
```

**Step 4: Test Endpoints**
```bash
# Test health check
curl http://localhost:8080/health

# Test processing with sample data
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{"input_path": "test_data.json"}'

# Check pipeline status
curl http://localhost:8080/status

# View review queue
curl http://localhost:8080/queue
```

### Option 2: Docker Testing

**Step 1: Build Container**
```bash
docker build -t job-pipeline .
```

**Step 2: Run Container**
```bash
# Run with environment file
docker run -p 8080:8080 --env-file .env job-pipeline

# Or run with individual environment variables
docker run -p 8080:8080 \
  -e SUPABASE_URL=your_url \
  -e SUPABASE_KEY=your_key \
  -e GEMINI_API_KEY=your_key \
  -e XANO_API_URL=your_url \
  -e XANO_API_KEY=your_key \
  job-pipeline
```

**Step 3: Test Container**
```bash
# Health check
curl http://localhost:8080/health

# Process sample data (copy test file into container first)
docker cp test_data.json <container_id>:/app/test_data.json
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{"input_path": "test_data.json"}'
```

### Option 3: Google Cloud Run Testing

**Step 1: Deploy to Cloud Run**
```bash
# Set your project
export GOOGLE_CLOUD_PROJECT=your-project-id

# Deploy
./deploy.sh

# Set environment variables
./set-env-vars.sh
```

**Step 2: Test Deployed Service**
```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe job-pipeline \
  --region=us-central1 --format='value(status.url)')

# Health check
curl $SERVICE_URL/health

# Process remote data
curl -X POST $SERVICE_URL/process \
  -H "Content-Type: application/json" \
  -d '{"input_path": "https://example.com/your-job-feed.xml"}'

# Check status
curl $SERVICE_URL/status
```

## 📊 Test Data Formats

### Sample JSON Data (Included: test_data.json)
```json
[
  {
    "requisition_id": "test-001",
    "position_title": "Senior Python Developer", 
    "job_details": "Build scalable web applications...",
    "hiring_organization": "TechCorp Inc.",
    "publication_date": "2024-01-15T10:00:00Z",
    "apply_url": "https://techcorp.com/jobs/python-dev",
    "employmentType": "FULL_TIME",
    "isRemote": true
  }
]
```

### Sample XML Data
```xml
<?xml version="1.0"?>
<jobs>
  <job>
    <id>xml-001</id>
    <title>Data Scientist</title>
    <company>DataCorp</company>
    <description>Analyze large datasets...</description>
    <posted>2024-01-15T10:00:00Z</posted>
    <location>New York</location>
  </job>
</jobs>
```

### Sample CSV Data
```csv
id,title,company,description,posted_date,location
csv-001,DevOps Engineer,CloudTech,Manage infrastructure...,2024-01-15,Remote
csv-002,Frontend Developer,WebCorp,Build user interfaces...,2024-01-16,San Francisco
```

## ✅ Expected Test Results

### Health Check Response
```json
{
  "status": "healthy",
  "service": "Job Data Ingestion Pipeline", 
  "version": "1.0.0"
}
```

### Successful Processing Response
```json
{
  "success": true,
  "input_path": "test_data.json",
  "jobs_processed": 2,
  "jobs_inserted": 2, 
  "jobs_closed": 0,
  "jobs_auto_approved": 1,
  "jobs_manual_review": 1,
  "errors": []
}
```

### Pipeline Status Response
```json
{
  "pipeline_status": "ready",
  "confidence_threshold": 0.86,
  "review_queue": {
    "total_items": 1,
    "pending_items": 1,
    "queue_file": "manual_review_queue.json"
  }
}
```

## 🚨 Troubleshooting

### Common Issues and Solutions

**Issue: "ModuleNotFoundError" when running locally**
```bash
# Solution: Use virtual environment Python directly
./venv/bin/python app.py
# Instead of just: python app.py
```

**Issue: "Invalid API key" errors**
```bash
# Solution: Check your .env file has correct credentials
cat .env
# Make sure all required variables are set with real values
```

**Issue: Docker build fails**
```bash
# Solution: Check .dockerignore doesn't exclude required files
# Make sure requirements.txt is included (not ignored)
```

**Issue: Cloud Run deployment fails**
```bash
# Solution: Check you have the required permissions
gcloud auth list
gcloud projects list
gcloud auth application-default login
```

**Issue: Jobs not processing correctly**
```bash
# Solution: Check the manual review queue
curl http://localhost:8080/queue
# Low-confidence jobs go to manual review by design
```

## 📈 Performance Testing

### Load Testing
```bash
# Test with multiple requests
for i in {1..10}; do
  curl -X POST http://localhost:8080/process \
    -H "Content-Type: application/json" \
    -d '{"input_path": "test_data.json"}' &
done
wait
```

### Memory Testing
```bash
# Monitor Docker container resources
docker stats job-pipeline
```

## 🎯 Testing Checklist

- [ ] ✅ Health endpoint responds
- [ ] ✅ Sample data processes successfully  
- [ ] ✅ Jobs are validated and transformed
- [ ] ✅ AI enrichment runs (with real API keys)
- [ ] ✅ High confidence jobs auto-approve
- [ ] ✅ Low confidence jobs go to review queue
- [ ] ✅ Error handling works gracefully
- [ ] ✅ Docker container builds and runs
- [ ] ✅ Cloud Run deployment succeeds
- [ ] ✅ Environment variables are secure

## 🚀 Ready for Production

Once all tests pass, your pipeline is ready to process real job feeds at scale!

**Remember**: Replace the mock credentials in `.env` with your real API keys before production use.