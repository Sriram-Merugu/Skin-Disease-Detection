from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from ultralytics import YOLO
import numpy as np
import shutil
import os
import json
from PIL import Image

# Initialize FastAPI app
app = FastAPI()

# Load YOLO model with error handling
try:
    model = YOLO(r"./model/best.pt")
except Exception as e:
    raise RuntimeError(f"Model loading failed: {e}")


# Load disease information from JSON file
def load_disease_info():
    try:
        with open("disease_info.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Disease information file not found.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding disease information file.")


disease_info = load_disease_info()

# Setup static files and templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# Routes
@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload_form.html", {"request": request})


@app.post("/upload/", response_class=HTMLResponse)
async def classify_image(request: Request, file: UploadFile = File(...)):
    try:
        # Save the uploaded file temporarily
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, file.filename)

        with open(temp_file_path, "wb") as temp_file:
            shutil.copyfileobj(file.file, temp_file)

        # Run YOLO model on the image
        results = model(temp_file_path)
        names_dict = results[0].names
        probs = results[0].probs.data.tolist()

        # Find the classified label
        classified_label = names_dict[np.argmax(probs)]
        cleaned_label = ' '.join(classified_label.split('_'))  # Clean label formatting

        # Clean up the temporary file
        os.remove(temp_file_path)

        # Fetch disease information
        disease_data = disease_info.get(cleaned_label, {"Description": "No data available", "Recommendations": {}})

        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "label": cleaned_label,
                "filename": file.filename,
                "description": disease_data.get("Description", "No description available"),
                "recommendations": disease_data.get("Recommendations", {})
            },
        )
    except Exception as e:
        return HTMLResponse(content=f"An error occurred: {str(e)}", status_code=500)
