from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from Parse import parse

app = FastAPI()

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
async def parse_schedule(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        return JSONResponse(content={"message": "Invalid file type"}, status_code=400)
    try:
        response = await parse(file)
        return response
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

