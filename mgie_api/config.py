APP_NAME = "T-Bank image editor"
APP_VERSION = "1.0"
IS_DEBUG = False

PATH_LLAVA="./_ckpt/LLaVA-7B-v1"
PATH_MLLM="./_ckpt/mgie_7b/mllm.pt"
PATH_UNET="./_ckpt/mgie_7b/unet.pt"
PATH_PIX2PIX="timbrooks/instruct-pix2pix"
DEVICE="cuda"

SPECIAL_TOKENS = ['[IMG0]', '[IMG1]', '[IMG2]', '[IMG3]', '[IMG4]', '[IMG5]', '[IMG6]', '[IMG7]']
DEFAULT_IMAGE_TOKEN = '<image>'
DEFAULT_IMAGE_PATCH_TOKEN = '<im_patch>'
DEFAULT_IM_START_TOKEN = '<im_start>'
DEFAULT_IM_END_TOKEN = '<im_end>'

BASIC_PROMPT = "what will this image be like if"
