import os

from dotenv import load_dotenv

index_model_prompt = """You are a model designed to assist an image generator in determining which image the user wants to modify.
There are three images in the following order: 
- image1: the oldest (two steps ago).
- image2: the previous (one step ago).
- image3: the most recent (latest).

The user's request is: {}

Respond with the image number the user wants to modify. 
Only output one of these options exactly as written: image1, image2, image3."""

summarized_model_prompt = """You are a model designed to assist an image generator in writing new prompt from old prompts.
There are three sentences in the following order: {}. 

Respond with the new prompt. Don't add any information that is out of context.
Only output one sentence without any other words.
"""

class Config:
    def __init__(self):
        load_dotenv()


        self.UPLOAD_FOLDER_  = os.getenv('UPLOAD_FOLDER')
        self.context_length_ = int(os.getenv('CONTEXT_LENGHT'))
        self.text_context_length_ = int(os.getenv('CONTEXT_LENGHT'))
        self.max_trys_ = int(os.getenv("MAX_TRYS"))

        self.ml_llm_worker_url_ = os.getenv('ML_WORKER_LLM_URL')
        self.ml_image_worker_url_ = os.getenv('ML_WORKER_IMAGE_URL')

        self.prompt_for_question_preprocess_model_ = os.getenv('PROMT_FOR_QUESTION_MODEL')

        self.port_ = int(os.getenv("SERVER_PORT"))

        self.index_model_prompt_ = index_model_prompt
        self.summarized_model_prompt_ = summarized_model_prompt

    @property
    def index_model_prompt(self):
        return self.index_model_prompt_

    @property
    def port(self):
        return self.port_
    
    @property
    def summarized_model_prompt(self):
        return self.summarized_model_prompt_


    @property
    def max_trys(self):
        return self.max_trys_

    @property
    def UPLOAD_FOLDER(self):
        return self.UPLOAD_FOLDER_

    @property
    def context_length(self):
        return self.context_length_

    @property
    def ml_llm_worker_url(self):
        return self.ml_llm_worker_url_

    @property
    def ml_image_worker_url(self):
        return self.ml_image_worker_url_

    @property
    def prompt_for_question_preprocess_model(self):
        return self.prompt_for_question_preprocess_model_

    @property
    def text_context_length(self):
        return self.text_context_length_


cfg = Config()