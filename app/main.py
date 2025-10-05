from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import logging
import sys

from app.Parse import parse
from app.config import config
from app.metrics import metrics, track_time

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

app = FastAPI()

logger = logging.getLogger(__name__)
logger.info("Starting FastAPI application")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

logger.info(f"CORS configured with allowed origins: {config.ALLOWED_ORIGINS}")

@app.get("/")
async def root():
    logger.info("Called root route")
    return {"message": "Hello World"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "schedule-parser"
    }


@app.get("/metrics")
async def get_metrics():
    """Get current metrics statistics"""
    stats = metrics.get_stats()
    return stats


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

# My catch all code
@app.api_route("/{path_name:path}", methods=["GET"])
async def catch_all(request: Request, path_name: str):
   return {"request_method": request.method, "path_name": path_name}

@app.post("/parse")
@track_time("parse_request")
async def parse_schedule(file: UploadFile = File(...), browser: str = Form(default="CHROME")):
    logger.info(f"Received parse request for file: {file.filename}, browser: {browser}")
    metrics.increment("requests_total")

    # Validate file size
    if file.size > config.MAX_FILE_SIZE:
        logger.warning(f"File rejected - size {file.size} bytes exceeds limit of {config.MAX_FILE_SIZE} bytes")
        metrics.increment("requests_failed")
        metrics.record_error("file_too_large", f"File size: {file.size}")
        return JSONResponse(content={"message": "File too large"}, status_code=413)

    # Validate browser parameter
    if browser.upper() not in config.VALID_BROWSERS:
        logger.warning(f"Invalid browser parameter: {browser}. Valid options: {config.VALID_BROWSERS}")
        metrics.increment("requests_failed")
        metrics.record_error("invalid_browser", f"Browser: {browser}")
        return JSONResponse(content={"message": "Invalid browser"}, status_code=400)

    # Validate content type
    if file.content_type not in config.ALLOWED_CONTENT_TYPES:
        logger.warning(f"Invalid file type: {file.content_type}. Expected: {config.ALLOWED_CONTENT_TYPES}")
        metrics.increment("requests_failed")
        metrics.record_error("invalid_content_type", f"Type: {file.content_type}")
        return JSONResponse(content={"message": "Invalid file type"}, status_code=400)

    try:
        logger.info(f"Starting parse process for {file.filename} with {browser} browser settings")
        browser = browser.upper()
        response = await parse(file, browser)
        logger.info(f"Successfully generated calendar for {file.filename}")
        metrics.increment("requests_success")
        metrics.log_metrics()

        return Response(
        content=response,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f"attachment; filename={config.CALENDAR_FILENAME}"
        })
    except ValueError as e:
        logger.warning(f"Validation error while parsing {file.filename}: {e}")
        metrics.increment("requests_failed")
        metrics.record_error("validation_error", str(e))
        return JSONResponse(
            content={"error": "Validation error", "message": "Invalid input data"},
            status_code=400
        )
    except HTTPException as e:
        # Re-raise HTTP exceptions (like from ParsePDF)
        logger.warning(f"HTTP error while parsing {file.filename}: {e.detail}")
        metrics.increment("requests_failed")
        metrics.record_error("http_exception", e.detail)
        raise
    except Exception as e:
        logger.error(f"Internal server error while parsing {file.filename}: {e}", exc_info=True)
        metrics.increment("requests_failed")
        metrics.record_error("internal_error", str(e))
        return JSONResponse(
            content={"error": "Internal server error", "message": "Failed to process the file. Please ensure it's a valid schedule PDF."},
            status_code=500
        )

handler = Mangum(app)

