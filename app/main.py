from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import logging

from app.Parse import parse

app = FastAPI()


logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info("Starting uvicorn server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    logger.info("Called root route")
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

# My catch all code
@app.api_route("/{path_name:path}", methods=["GET"])
async def catch_all(request: Request, path_name: str):
   return {"request_method": request.method, "path_name": path_name}

@app.post("/parse")
async def parse_schedule(file: UploadFile = File(...), browser: str = Form(default="CHROME")):
    logger.info("Parsing schedule")
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    if file.size > MAX_FILE_SIZE:
        logger.warning(f"File size {file.size} exceeds limit of {MAX_FILE_SIZE}")
        return JSONResponse(content={"message": "File too large"}, status_code=413)

    VALID_BROWSERS = ["CHROME", "FIREFOX"]
    if browser.upper() not in VALID_BROWSERS:
        logger.warning(f"Invalid browser {browser}")
        return JSONResponse(content={"message": "Invalid browser"}, status_code=400)

    if file.content_type != "application/pdf":
        logger.warning(f"Invalid file type {file.content_type}")
        return JSONResponse(content={"message": "Invalid file type"}, status_code=400)
    try:
        logger.info(f"Parsing file {file.filename} with browser {browser}")
        browser = browser.upper()
        response = await parse(file, browser)
        return Response(
        content=response,
        media_type="text/calendar",
        headers={
            "Content-Disposition": "attachment; filename=calendar.ics"
        })
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        return JSONResponse(content={"error": "Validation error", "details": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Internal server error: {e}")
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)

handler = Mangum(app)

