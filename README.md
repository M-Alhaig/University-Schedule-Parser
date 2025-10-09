# FastAPI Schedule Parser - Project Overview

## What is This?

FastAPI Schedule Parser is an intelligent PDF-to-calendar converter designed specifically for university course schedules. It automatically extracts course information from table-based schedule PDFs and converts them into standard ICS calendar files that can be imported into any calendar application (Google Calendar, Outlook, Apple Calendar, etc.).

## The Problem It Solves

Universities typically distribute course schedules as PDF documents with tabular layouts showing days, times, and course details. Manually entering dozens of courses into a calendar is time-consuming and error-prone. This service automates the entire process:

- **Input**: University schedule PDF (multi-page, various browser formats)
- **Output**: ICS calendar file with all courses as recurring weekly events
- **Processing Time**: Typically 2-5 seconds per schedule

## How It Works

The system uses a multi-stage pipeline combining computer vision and OCR to transform static PDFs into structured calendar data.

### Processing Pipeline

#### 1. PDF Processing
- **Detects orientation**: Automatically identifies portrait vs landscape layouts
- **Handles multi-page PDFs**: Intelligently merges multiple pages into a single schedule image
  - Finds table boundaries on page 1 using vertical line detection
  - Locates duplicate header rows on page 2 using OCR and horizontal line detection
  - Crops and merges pages at precise boundaries (no hardcoded values)
- **Converts to image**: Renders PDF pages at high DPI (300) for optimal OCR

**Key Innovation**: Dynamic boundary detection eliminates hardcoded crop values. The system automatically finds where tables start and end by detecting structural elements (lines, repeated headers).

#### 2. Image Enhancement
- **Keyword detection**: Locates a reference keyword (default: "THURSDAY") in the schedule header
- **Table edge identification**: Finds horizontal lines below the keyword to determine table right edge
- **Separator insertion**: Draws vertical lines to improve cell boundary detection
- **Output**: Enhanced image optimized for box extraction

#### 3. Box Extraction (Computer Vision)
Uses OpenCV morphological operations to detect table structure:
- **Erosion/dilation**: Identifies rectangular regions representing schedule cells
- **Contour detection**: Finds boundaries of each table cell
- **Filtering**: Removes false positives based on area, aspect ratio, and dimensions
- **Deduplication**: Uses IoU (Intersection over Union) to eliminate overlapping boxes
- **Sorting**: Orders boxes top-to-bottom, left-to-right for processing

**Result**: Precise coordinates for every cell in the schedule table

#### 4. Day/Time Detection (OCR)
- **Day headers**: OCR on top row to identify day columns (SUNDAY-SATURDAY, supports French)
- **Time reference box**: Locates first box containing HH:MM pattern
- **Column mapping**: Associates each box with its day column based on horizontal position

#### 5. Subject Extraction (Parallel Processing)
Uses ThreadPoolExecutor for concurrent processing:
- For each detected box:
  - Determines which day it belongs to (based on x-coordinate)
  - Extracts course text via Tesseract OCR
  - Extracts time range from corresponding time box
  - Handles various OCR time formats: "08:00 - 09:00", "08:00-09:00", etc.
- Filters out time reference boxes and empty cells

#### 6. Course Parsing (Structured Extraction)
Applies regex patterns to extract:
- **Course name**: Full title of the course
- **Course ID**: Unique identifier (e.g., "CS101")
- **Activity type**: Lecture, Lab, Tutorial, etc.
- **Section number**: Section identifier
- **Campus/Location**: Building and room number
- **Duration**: Validated time range (HH:MM-HH:MM)

Creates Pydantic models for type-safe course data

#### 7. Calendar Generation (ICS Creation)
- **Time parsing**: Converts duration strings to start/end times
- **Day mapping**: Maps day names to weekday numbers (0=Monday, 6=Sunday)
- **Date calculation**: Finds next occurrence of each day from current date
- **Recurring events**: Creates weekly recurring events for configurable duration (default: 19 weeks)
- **Timezone support**: Handles multiple timezones (KSA/Riyadh, ALG/Algiers)
- **Standard format**: Generates RFC 5545 compliant ICS files

### Architecture Diagram

```
┌─────────────────┐
│   Upload PDF    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PDF Processing  │  ◄── Detects orientation, merges pages
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Image Enhancement│ ◄── Finds keyword, draws separators
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Box Extraction  │  ◄── OpenCV: detects cells, filters, sorts
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Day/Time OCR    │  ◄── Identifies columns and time boxes
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Parallel OCR    │  ◄── ThreadPoolExecutor: extracts all courses
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Course Parsing  │  ◄── Regex: structures raw text
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ICS Generation  │  ◄── Creates recurring calendar events
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Download ICS   │
└─────────────────┘
```

## Key Technical Features

### Dynamic Detection (No Hardcoded Values)
Unlike traditional document processing systems, this project doesn't rely on fixed crop coordinates or table positions. Instead:
- **Vertical line detection** finds table boundaries dynamically
- **Horizontal line detection** identifies header separators
- **OCR-based positioning** locates structural elements (keywords, day names)

This makes the system robust to different PDF formats, page sizes, and table layouts.

### Intelligent Multi-Page Handling
The system automatically:
1. Detects when a schedule spans multiple pages
2. Finds exact boundaries using structural analysis
3. Merges pages seamlessly without losing data
4. Handles edge cases (missing lines, OCR errors) with fallback strategies

### Parallel Processing
Subject extraction uses concurrent processing (ThreadPoolExecutor) to:
- Process multiple boxes simultaneously
- Reduce overall processing time by 3-5x
- Maintain thread-safe operations
- Handle large schedules efficiently

### Robust OCR Error Handling
Time parsing handles various OCR artifacts:
- Extra dashes: "08:00--09:00"
- Extra spaces: "08:00 - - 09:50"
- Missing separators: "08:0009:00"
- Strips invalid characters before parsing

## Technology Stack

- **FastAPI**: Modern async web framework for API endpoints
- **Tesseract OCR**: Open-source OCR engine for text extraction
- **OpenCV**: Computer vision library for image processing and box detection
- **PyMuPDF (fitz)**: PDF rendering and manipulation
- **icalendar**: ICS file generation
- **AWS Lambda**: Serverless deployment with Docker containers
- **API Gateway**: Rate limiting, API key management, and monitoring

## Deployment

The system is designed for serverless deployment:
- **Container-based**: Docker image with all dependencies (Tesseract, Poppler, OpenCV)
- **AWS Lambda**: Runs on-demand with automatic scaling
- **API Gateway**: Provides authentication, rate limiting, and usage tracking
- **Stateless**: No database required, fully event-driven

## Performance Characteristics

- **Processing time**: 2-5 seconds per schedule (varies with complexity)
- **Concurrency**: Handles multiple requests simultaneously via Lambda scaling
- **Memory usage**: ~1GB during peak processing (Lambda configuration)
- **Accuracy**: >95% course extraction accuracy on standard formats

## Use Cases

1. **Student Automation**: Students upload their schedule PDF and import the ICS file into their preferred calendar app
2. **University Portals**: Integration with student portals for one-click schedule export
3. **Batch Processing**: Process entire class schedules for administrative purposes
4. **Calendar Integration**: Direct integration with calendar APIs (Google Calendar, Outlook)

## Extensibility

The modular design allows easy customization:
- **Configuration**: All thresholds and parameters are externalized
- **OCR Languages**: Supports multiple languages (currently English/French)
- **Browser Formats**: Handles different PDF rendering engines (Chrome, Firefox)
- **Timezone Support**: Easy to add new timezones
- **Export Formats**: Architecture supports adding other calendar formats (JSON, CSV, etc.)

## Why This Approach?

Traditional document parsing often relies on:
- Fixed positions/coordinates (brittle)
- Template matching (requires training data)
- Rule-based systems (hard to maintain)

This project uses:
- **Structural analysis**: Finds elements based on visual structure
- **Dynamic detection**: Adapts to different layouts
- **Hybrid approach**: Combines CV and OCR for robustness
- **Fallback strategies**: Degrades gracefully when detection fails

The result is a system that works across different universities, PDF formats, and schedule layouts without requiring retraining or manual configuration.
