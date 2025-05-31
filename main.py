from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from Parse import parse

app = FastAPI()
logger = logging.getLogger("uvicorn")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["POST"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

@app.post("/parse")
async def parse_schedule(file: UploadFile = File(...), browser: str = Form(default="CHROME")):
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    if file.size > MAX_FILE_SIZE:
        return JSONResponse(content={"message": "File too large"}, status_code=413)

    VALID_BROWSERS = ["CHROME", "FIREFOX"]
    if browser.upper() not in VALID_BROWSERS:
        return JSONResponse(content={"message": "Invalid browser"}, status_code=400)

    if file.content_type != "application/pdf":
        return JSONResponse(content={"message": "Invalid file type"}, status_code=400)
    try:
        logger.info(f"Parsing file {file.filename} with browser {browser}")
        browser = browser.upper()
        response = await parse(file, browser)
        return response
    except ValueError as e:
        return JSONResponse(content={"error": "Validation error", "details": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)

