from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import io
import PIL
import base64
from typing import Dict
from pydantic import BaseModel

import uvicorn

from generate_image import MGIE_Model


class ImageTextPayload(BaseModel):
    image_bytes: str
    text: str


model = None
app = FastAPI()


origins = [
    "http://127.0.0.1",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate/")
async def generate(payload: ImageTextPayload):
    try:
        try:
            image_data = base64.b64decode(payload.image_bytes)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid image bytes provided.")
        
        if not payload.text:
            raise HTTPException(status_code=400, detail="Text field cannot be empty.")

        pil_image = PIL.Image.open(io.BytesIO(image_data))
        pil_image.save("ex.jpg")

        generated_result = await model.generate_image(pil_image, payload.text)

        byte_array = io.BytesIO()
        generated_result.save(byte_array, format='JPG')

        return {"generated_image_bytes": byte_array.getvalue()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

if __name__ == "__main__":
    model = MGIE_Model()
    uvicorn.run(app, host="127.0.0.1", port=8000)
