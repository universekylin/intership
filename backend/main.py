import os
import uuid
import requests
import time
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get environment variables
REPLICATE_TOKEN = os.getenv("REPLICATE_API_TOKEN")
DINO_VERSION = os.getenv("GROUNDING_DINO_VERSION")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")

# Directory to store uploaded and processed images
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Expand prompt to improve object detection accuracy
def expand_prompt(prompt):
    return f"{prompt}, a photo of {prompt}, {prompt} on the left, {prompt} close-up, {prompt} object"

# Upload image to imgbb for temporary URL access
def upload_to_imgbb(file_path):
    with open(file_path, "rb") as f:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            params={"key": IMGBB_API_KEY},
            files={"image": f}
        )
    response.raise_for_status()
    image_url = response.json()["data"]["url"]
    print(f"🌐 Uploaded to imgbb: {image_url}")
    return image_url

# Call Grounding DINO model on Replicate to detect bounding boxes
def detect_target_with_dino(image_url: str, prompt: str):
    print(f"🟢 Using prompt: '{prompt}'")

    endpoint = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": f"Token {REPLICATE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "version": DINO_VERSION,
        "input": {
            "image": image_url,
            "query": prompt,
            "box_threshold": 0.5,
            "text_threshold": 0.4
        }
    }

    res = requests.post(endpoint, headers=headers, json=payload)
    res.raise_for_status()
    data = res.json()
    status_url = data["urls"]["get"]

    # Poll until prediction completes
    while True:
        poll = requests.get(status_url, headers=headers)
        poll.raise_for_status()
        poll_data = poll.json()
        status = poll_data["status"]
        print(f"🔄 Replicate status: {status}")
        if status == "succeeded":
            break
        elif status == "failed":
            raise Exception("Grounding DINO prediction failed.")
        time.sleep(2)

    print("📦 Full DINO response:", poll_data)
    output = poll_data.get("output", {})
    detections = output.get("detections", [])
    boxes = [d["bbox"] for d in detections if "bbox" in d]
    print("🎯 Detected boxes:", boxes)
    return boxes

# Apply blur mask to detected bounding boxes in the image
def apply_mask(image_path, boxes):
    image = cv2.imread(image_path)

    for box in boxes:
        x1, y1, x2, y2 = map(int, box)
        region = image[y1:y2, x1:x2]
        blurred = cv2.GaussianBlur(region, (131, 131), 0)
        image[y1:y2, x1:x2] = blurred

    result_path = os.path.join(UPLOAD_DIR, f"masked_{uuid.uuid4().hex}.jpg")
    cv2.imwrite(result_path, image)
    return result_path

# Main API route for masking image targets
@app.post("/mask")
async def mask_target(file: UploadFile, prompt: str = Form(...)):
    print(f"🟢 Prompt received: {prompt}")

    try:
        # Save uploaded image locally
        filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        print(f"📦 Image saved at: {file_path}")

        # Upload image and detect target object
        image_url = upload_to_imgbb(file_path)
        boxes = detect_target_with_dino(image_url, prompt)

        if not boxes:
            return JSONResponse(content={"error": "No object detected."}, status_code=200)

        # Apply masking and return masked image URL
        masked_path = apply_mask(file_path, boxes)
        masked_url = upload_to_imgbb(masked_path)
        return JSONResponse(content={"result_url": masked_url})

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
