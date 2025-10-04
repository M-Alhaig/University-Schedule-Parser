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

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
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

**Response:**
- Success: ICS file download (200)
- File too large: Error message (413)
- Invalid browser: Error message (400)
- Invalid file type: Error message (400)
- Processing error: Error message (500)

## Configuration

Edit `app/config.py` to customize:

### File Validation
```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
VALID_BROWSERS = ["CHROME", "FIREFOX"]
```

### PDF Crop Points
Adjust crop points for different browser PDF formats:
```python
PDF_CROP_POINTS = {
    "CHROME": {"page1_crop": 14.5, "page2_crop": 40.0},
    "FIREFOX": {"page1_crop": 14.5, "page2_crop": 14.5}
}
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

3. **Add Function URL or API Gateway**
   - Enable Function URL for direct HTTPS endpoint
   - Or create API Gateway REST API

## Project Structure

```
FastAPIScheduleParser/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application and endpoints
│   ├── config.py         # Configuration settings
│   ├── Parse.py          # Main parsing orchestration
│   ├── ParsePDF.py       # PDF processing logic
│   ├── ParseImg.py       # Image processing logic
│   └── IcsService.py     # ICS calendar generation
├── Tesseract-OCR/        # Windows only - Tesseract executable
├── poppler/              # Windows only - Poppler binaries
├── .dockerignore
├── .gitignore
├── Dockerfile            # AWS Lambda container config
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
- Increase DPI in config: `OCR_DPI = 400`
- Ensure PDF quality is good (not scanned at low resolution)
- Check Tesseract language data is installed

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
# TODO: Add pytest tests
pytest tests/
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
