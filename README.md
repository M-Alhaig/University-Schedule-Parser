# FastAPI Schedule Parser

A FastAPI-based service that converts university schedule PDFs into ICS calendar files. The service uses OCR (Tesseract) and computer vision (OpenCV) to extract course information from schedule PDFs and generates recurring calendar events.

## Features

- **PDF Processing**: Handles PDFs from different browsers (Chrome, Firefox)
- **Image Support**: Can process both PDF and image formats
- **OCR-based Extraction**: Uses Tesseract OCR for text extraction
- **Smart Box Detection**: Computer vision algorithms to detect schedule table cells
- **ICS Calendar Generation**: Creates standard ICS files with recurring events
- **AWS Lambda Ready**: Configured for serverless deployment with Docker
- **Multi-language Support**: Handles English and French day names
- **Configurable**: Externalized configuration for easy customization

## Prerequisites

### Local Development (Windows)

- Python 3.10+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) - Install and add to system PATH
- [Poppler](https://github.com/oschwartz10612/poppler-windows/releases/) - Extract to project directory as `poppler/`

### Local Development (Linux/Mac)

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils libgl1-mesa-glx libglib2.0-0

# macOS
brew install tesseract poppler
```

### Docker/Production

All dependencies are included in the Docker image.

## Installation

### Local Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd FastAPIScheduleParser
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install system dependencies**

   **Windows:**
   - Install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
   - Download [Poppler](https://github.com/oschwartz10612/poppler-windows/releases/)
   - Extract Poppler to project directory as `poppler/`
   - Extract Tesseract to project directory as `Tesseract-OCR/`

   **Linux/Ubuntu:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y tesseract-ocr poppler-utils libgl1-mesa-glx libglib2.0-0
   ```

   **macOS:**
   ```bash
   brew install tesseract poppler
   ```

4. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment (optional)**
   ```bash
   cp .env.example .env
   # Edit .env to customize settings
   ```

6. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at `http://localhost:8000`

### Docker Setup

1. **Build the Docker image**
   ```bash
   docker build -t schedule-parser .
   ```

2. **Run locally with Docker**
   ```bash
   docker run -p 9000:8080 schedule-parser
   ```

3. **Test the Lambda handler**
   ```bash
   curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
   ```

## API Documentation

### Endpoints

#### `GET /`
Health check endpoint.

**Response:**
```json
{
  "message": "Hello World"
}
```

#### `GET /health`
Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "service": "schedule-parser"
}
```

#### `GET /metrics`
Get current metrics and statistics.

**Response:**
```json
{
  "requests_total": 150,
  "requests_success": 142,
  "requests_failed": 8,
  "success_rate": 94.67,
  "avg_processing_time_ms": 2341.23,
  "min_processing_time_ms": 1205.45,
  "max_processing_time_ms": 5432.12,
  "recent_errors_count": 8
}
```

#### `POST /parse`
Upload a schedule PDF and receive an ICS calendar file.

**Parameters:**
- `file` (required): PDF file (max 10MB)
- `browser` (optional): Browser type - `CHROME` or `FIREFOX` (default: `CHROME`)

**Example using cURL:**
```bash
curl -X POST "http://localhost:8000/parse" \
  -F "file=@schedule.pdf" \
  -F "browser=CHROME" \
  -o calendar.ics
```

**Example using Python:**
```python
import requests

with open('schedule.pdf', 'rb') as f:
    files = {'file': f}
    data = {'browser': 'CHROME'}
    response = requests.post('http://localhost:8000/parse', files=files, data=data)

    with open('calendar.ics', 'wb') as ics:
        ics.write(response.content)
```

**With API Gateway (Production):**
```bash
curl -X POST "https://api-id.execute-api.region.amazonaws.com/prod/parse" \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@schedule.pdf" \
  -F "browser=CHROME" \
  -o calendar.ics
```

**Response:**
- Success: ICS file download (200)
- File too large: Error message (413)
- Invalid browser: Error message (400)
- Invalid file type: Error message (400)
- Processing error: Error message (500)

**See `examples/sample_usage.py` for complete Python examples.**

## Configuration

Configuration can be set via environment variables or by editing `app/config.py`.

### Environment Variables

All configuration values support environment variable overrides:

```bash
# File validation
export MAX_FILE_SIZE=10485760              # 10MB in bytes
export ALLOWED_CONTENT_TYPES="application/pdf"

# OCR settings
export OCR_DPI=300
export DETECTION_KEYWORD="THURSDAY"
export KEYWORD_RIGHT_PADDING=100           # Fallback padding to right of keyword

# Vertical line detection (dynamic table boundary detection)
export VERTICAL_LINE_MIN_LENGTH=30
export VERTICAL_KERNEL_HEIGHT=50
export VERTICAL_KERNEL_WIDTH=1
export EDGE_CLUSTER_THRESHOLD=20
export MIN_VERTICAL_LINES_COUNT=3

# Box extraction
export BOX_MIN_WIDTH=50
export BOX_MIN_HEIGHT=20
export BOX_AREA_THRESHOLD_PDF=20000
export BOX_IOU_THRESHOLD=0.1

# Processing
export MAX_WORKERS=8

# Calendar settings
export SCHEDULE_DURATION_WEEKS=19
export DEFAULT_TIMEZONE="KSA"
export CALENDAR_FILENAME="calendar.ics"
```

### Configuration File

Alternatively, edit `app/config.py` directly:

### Dynamic Table Boundary Detection
The system uses vertical line detection to automatically find table boundaries (no hardcoded crop values):
```python
# Vertical line detection parameters
VERTICAL_LINE_MIN_LENGTH = 30           # Minimum line length to detect
VERTICAL_KERNEL_HEIGHT = 50             # Morphological kernel height
VERTICAL_KERNEL_WIDTH = 1               # Morphological kernel width
EDGE_CLUSTER_THRESHOLD = 20             # Pixel threshold for line clustering
MIN_VERTICAL_LINES_COUNT = 3            # Minimum lines to confirm table
```

### Image Processing Thresholds
```python
BOX_EXTRACTION = {
    "min_width": 50,
    "min_height": 20,
    "area_threshold_pdf": 20000,
    "area_threshold_image": 2000,
    ...
}
```

### Calendar Settings
```python
SCHEDULE_DURATION_WEEKS = 19  # Number of weeks for recurring events
DEFAULT_TIMEZONE = "KSA"      # KSA (Asia/Riyadh) or ALG (Africa/Algiers)
```

## AWS Lambda Deployment

### Build and Push to ECR

1. **Create ECR repository**
   ```bash
   aws ecr create-repository --repository-name schedule-parser
   ```

2. **Authenticate Docker to ECR**
   ```bash
   aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
   ```

3. **Tag and push image**
   ```bash
   docker tag schedule-parser:latest <account-id>.dkr.ecr.<region>.amazonaws.com/schedule-parser:latest
   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/schedule-parser:latest
   ```

### Create Lambda Function

1. **Create function from container image**
   - Function name: `schedule-parser`
   - Container image URI: `<account-id>.dkr.ecr.<region>.amazonaws.com/schedule-parser:latest`
   - Architecture: x86_64

2. **Configure function**
   - Memory: 1024 MB (minimum recommended)
   - Timeout: 60 seconds
   - Environment variables: (if needed)

### Setup API Gateway (Recommended)

**Why API Gateway?**
- Built-in API key management
- Built-in rate limiting (throttling)
- Request validation
- Usage plans and quotas
- Cost tracking per API key

**Setup Steps:**

1. **Create REST API**
   ```bash
   aws apigateway create-rest-api --name schedule-parser-api --endpoint-configuration types=REGIONAL
   ```

2. **Create API Key**
   ```bash
   # Create API key
   aws apigateway create-api-key --name schedule-parser-key --enabled

   # Note the API key ID and value
   ```

3. **Create Usage Plan**
   ```bash
   # Create usage plan with rate limiting
   aws apigateway create-usage-plan \
     --name schedule-parser-plan \
     --throttle burstLimit=10,rateLimit=5 \
     --quota limit=1000,period=MONTH

   # Associate API key with usage plan
   aws apigateway create-usage-plan-key \
     --usage-plan-id <usage-plan-id> \
     --key-id <api-key-id> \
     --key-type API_KEY
   ```

4. **Configure API Gateway to Lambda Integration**
   - Create resource: `/parse`
   - Create method: `POST`
   - Integration type: Lambda Function
   - Lambda Function: `schedule-parser`
   - Enable API Key Required: Yes

5. **Deploy API**
   ```bash
   aws apigateway create-deployment \
     --rest-api-id <api-id> \
     --stage-name prod
   ```

**Rate Limiting Configuration:**
- **Burst Limit**: 10 requests - Maximum concurrent requests
- **Rate Limit**: 5 requests/second - Steady-state request rate
- **Quota**: 1000 requests/month - Monthly usage limit (optional)

**Using the API with API Key:**
```bash
curl -X POST "https://<api-id>.execute-api.<region>.amazonaws.com/prod/parse" \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@schedule.pdf" \
  -F "browser=CHROME" \
  -o calendar.ics
```

**Alternative: Function URL (Not Recommended for Production)**
- Enable Function URL for direct HTTPS endpoint
- No built-in authentication or rate limiting
- Suitable only for development/testing

## Monitoring & Metrics

The application includes built-in metrics collection for monitoring:

### Available Metrics

- **requests_total**: Total number of parse requests
- **requests_success**: Successful parse requests
- **requests_failed**: Failed parse requests
- **success_rate**: Percentage of successful requests
- **avg_processing_time_ms**: Average processing time
- **min/max_processing_time_ms**: Min and max processing times
- **recent_errors_count**: Count of recent errors

### Accessing Metrics

```bash
# Get current metrics
curl http://localhost:8000/metrics

# Response example
{
  "requests_total": 150,
  "requests_success": 142,
  "requests_failed": 8,
  "success_rate": 94.67,
  "avg_processing_time_ms": 2341.23
}
```

### CloudWatch Integration

Metrics are logged in JSON format for CloudWatch Logs Insights:

```
# CloudWatch Logs Insights query
fields @timestamp, @message
| filter @message like /METRICS:/
| parse @message "METRICS: *" as metrics_json
| display @timestamp, metrics_json
```

### CloudWatch Alarms (Recommended)

Create alarms for production monitoring:

```bash
# High error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name schedule-parser-high-error-rate \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold

# Long execution time alarm
aws cloudwatch put-metric-alarm \
  --alarm-name schedule-parser-slow-execution \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Average \
  --period 300 \
  --threshold 30000 \
  --comparison-operator GreaterThanThreshold
```

## Project Structure

```
FastAPIScheduleParser/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application and endpoints
│   ├── config.py         # Configuration with env var support
│   ├── metrics.py        # Metrics collection
│   ├── Parse.py          # Main parsing orchestration
│   ├── ParsePDF.py       # PDF processing logic
│   ├── ParseImg.py       # Image processing logic
│   └── IcsService.py     # ICS calendar generation
├── tests/                # Unit tests
│   ├── __init__.py
│   ├── test_parse.py
│   ├── test_ics_service.py
│   └── test_config.py
├── examples/
│   └── sample_usage.py   # Example API usage
├── Tesseract-OCR/        # Windows only - Tesseract executable
├── poppler/              # Windows only - Poppler binaries
├── .dockerignore
├── .gitignore
├── Dockerfile            # AWS Lambda container config
├── pytest.ini            # Pytest configuration
├── requirements.txt
└── README.md
```

## How It Works

1. **Upload**: User uploads a schedule PDF via `/parse` endpoint
2. **PDF Processing**:
   - Detects if text is embedded or image-based
   - Merges multi-page PDFs into single page
   - Adds separator lines for better detection
3. **Box Extraction**:
   - Converts to image and applies morphological operations
   - Detects table cell boundaries using contour detection
   - Filters duplicate boxes using IoU (Intersection over Union)
4. **OCR Processing**:
   - Extracts text from each detected box
   - Identifies day headers and time references
   - Parallel processing with ThreadPoolExecutor
5. **Course Parsing**:
   - Regex-based extraction of course details
   - Creates structured Course objects
6. **Calendar Generation**:
   - Generates ICS file with recurring weekly events
   - Configurable duration and timezone

## Logging

The application provides comprehensive logging:

- **INFO**: Key operations and progress
- **DEBUG**: Detailed processing information
- **WARNING**: Non-critical issues (missing keywords, failed parsing)
- **ERROR**: Critical failures with stack traces

Logs are output to stdout and can be viewed in:
- Local: Console output
- Docker: `docker logs <container-id>`
- AWS Lambda: CloudWatch Logs

## Troubleshooting

### "PDF format not supported"
- The keyword "THURSDAY" (or "JEUDI") was not found in the PDF
- Try a different browser parameter
- Verify the PDF contains a weekly schedule table

### Poor OCR results
- Increase DPI via environment variable: `export OCR_DPI=400`
- Ensure PDF quality is good (not scanned at low resolution)
- Check Tesseract language data is installed

### Configuration not applying
- Environment variables must be set before starting the application
- For Lambda: Set environment variables in Lambda function configuration
- For Docker: Use `-e` flag: `docker run -e OCR_DPI=400 ...`
- Restart application after changing configuration

### Lambda timeout
- Increase function timeout (60-120s recommended)
- Increase memory allocation (1024MB minimum)
- Consider pre-warming with scheduled events

### Import errors
- Ensure all files are in `app/` directory
- Check `PYTHONPATH` is set correctly in Docker
- Verify `__init__.py` exists in `app/`

## Development

### Running tests
```bash
# Install pytest (if not already installed)
pip install pytest

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_parse.py

# Run with coverage (requires pytest-cov)
pip install pytest-cov
pytest --cov=app --cov-report=html
```

### Code formatting
```bash
# Black formatter
black app/

# Sort imports
isort app/
```

### API Documentation
FastAPI provides automatic interactive documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - OCR engine
- [OpenCV](https://opencv.org/) - Computer vision library
- [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) - PDF processing
- [icalendar](https://github.com/collective/icalendar) - ICS generation
