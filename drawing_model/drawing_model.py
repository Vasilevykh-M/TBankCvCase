import base64
import io

import uvicorn
from fastapi import APIRouter, HTTPException, FastAPI
from kandinsky2 import get_kandinsky2
class DrawingModel:

    def __init__(self):
        self.model = get_kandinsky2('cuda', task_type='text2img', cache_dir='/tmp/kandinsky2', model_version='2.1', use_flash_attention=False)

    def __call__(self, prompt):
        images = self.model.generate_text2img(prompt, num_steps=100,
                                         batch_size=1, guidance_scale=4,
                                         h=1024, w=1024
                                         , sampler='p_sampler', prior_cf_scale=4,
                                         prior_steps="5")
        return images[0]

class DarwingApi:
    def __init__(self):
        self.router = APIRouter()
        self.router.add_api_route("/upload_image/", self.draw, methods=["POST"])
        self.model = DrawingModel()

    def draw(self, prompt):
        try:
            img = self.model(prompt)
            byte_array = io.BytesIO()
            img.save(byte_array, format='png')
            encoded_byte_array = base64.b64encode(byte_array.getvalue())

            return {"generated_image_bytes": encoded_byte_array}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

if __name__ == "__main__":
    api = DarwingApi()
    app = FastAPI()
    app.include_router(api.router)
    uvicorn.run(app, host="0.0.0.0", port=8080)