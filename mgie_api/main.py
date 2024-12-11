from fastapi import FastAPI, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware

import io
import PIL
import base64
from typing import Dict
from pydantic import BaseModel
from io import BytesIO


import uvicorn

from generate_image import MGIE_Model


model = None
app = FastAPI()


@app.post("/generate/")
async def generate(img_file: UploadFile = File(...), promt: str = ""):
    if all(ext not in img_file.filename for ext in ['.jpg', '.jpeg', '.png']):
        return HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f'File {img_file.filename} has unsupported extension type',
        )

    request_object_content = await img_file.read()
    pil_image = PIL.Image.open(BytesIO(request_object_content))

    try:

        pil_image.save("ex.jpg")

        generated_result = await model.generate_image(pil_image, promt)

        byte_array = io.BytesIO()
        generated_result.save(byte_array, format='JPG')

        return {"generated_image_bytes": byte_array.getvalue()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

if __name__ == "__main__":
    model = MGIE_Model()
    uvicorn.run(app, host="0.0.0.0", port=8000)
