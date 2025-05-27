from io import BytesIO

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
import fitz
from Parse import parse, Course

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

@app.post("/parse")
async def parse_schedule(file: UploadFile = File(...)):
    # if file.content_type != "application/pdf":
    #     return JSONResponse(content={"message": "Invalid file type"}, status_code=400)
    try:
        return await parse(file)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

