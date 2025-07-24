"""
Main Flask application for the Job Data Ingestion & Enrichment Pipeline.
"""
import asyncio
import logging
import os
from flask import Flask, request, jsonify
from src.config import Config
from src.pipeline import JobPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize pipeline
pipeline = None


def get_pipeline():
    """Get or create pipeline instance."""
    global pipeline
    if pipeline is None:
        try:
            Config.validate()
            pipeline = JobPipeline()
            logger.info("Pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            raise
    return pipeline


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    try:
        # Test database connection
        pipeline_instance = get_pipeline()
        pipeline_instance.db_service.get_existing_job_hashes()
        
        return jsonify({
            "status": "healthy",
            "service": "Job Data Ingestion Pipeline",
            "version": "1.0.0"
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


@app.route('/process', methods=['POST'])
def process_job_feed():
    """
    Process a job feed through the complete ETL pipeline.
    
    Expected JSON payload:
    {
        "input_path": "https://example.com/jobs.xml" or "/path/to/local/file.csv"
    }
    """
    try:
        # Get request data
        data = request.get_json()
        if not data or 'input_path' not in data:
            return jsonify({
                "error": "Missing 'input_path' in request body"
            }), 400
        
        input_path = data['input_path']
        logger.info(f"Processing job feed: {input_path}")
        
        # Get pipeline instance
        pipeline_instance = get_pipeline()
        
        # Run the pipeline asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(pipeline_instance.process_feed(input_path))
        finally:
            loop.close()
        
        # Return results
        if results['success']:
            logger.info(f"Pipeline completed successfully: {results}")
            return jsonify(results), 200
        else:
            logger.error(f"Pipeline failed: {results}")
            return jsonify(results), 500
            
    except Exception as e:
        logger.error(f"Error processing job feed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "input_path": data.get('input_path', 'unknown') if 'data' in locals() else 'unknown'
        }), 500


@app.route('/status', methods=['GET'])
def get_status():
    """Get pipeline status and queue information."""
    try:
        pipeline_instance = get_pipeline()
        queue_status = pipeline_instance.review_queue.get_queue_status()
        
        return jsonify({
            "pipeline_status": "ready",
            "confidence_threshold": Config.CONFIDENCE_THRESHOLD,
            "review_queue": queue_status
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({
            "error": str(e)
        }), 500


@app.route('/queue', methods=['GET'])
def get_review_queue():
    """Get the current manual review queue."""
    try:
        pipeline_instance = get_pipeline()
        queue_data = pipeline_instance.review_queue.load_review_queue()
        
        return jsonify({
            "queue": queue_data,
            "total_items": len(queue_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting review queue: {e}")
        return jsonify({
            "error": str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": [
            "GET /health - Health check",
            "POST /process - Process job feed",
            "GET /status - Get pipeline status",
            "GET /queue - Get review queue"
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": str(error)
    }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)