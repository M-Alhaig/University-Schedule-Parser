FROM python:3.10-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn numpy opencv-python pytesseract pydantic PIL icalendar pytz pdfplumber PyMuPDF
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]