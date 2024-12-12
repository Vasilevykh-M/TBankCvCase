import os

from dotenv import load_dotenv
class Config:
    def __init__(self):
        load_dotenv()


        self.UPLOAD_FOLDER_  = os.getenv('UPLOAD_FOLDER')
        self.context_length_ = int(os.getenv('CONTEXT_LENGHT'))
        self.text_content_length_ = int(os.getenv('CONTEXT_LENGHT'))
        self.max_trys_ = int(os.getenv("MAX_TRYS"))

        self.ml_server_url_ = os.getenv('ML_WORKER_PROMT')

        self.prompt_for_question_preprocess_model_ = os.getenv('PROMT_FOR_QUESTION_MODEL')

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
    def ml_server_url(self):
        return self.ml_server_url_

    @property
    def prompt_for_question_preprocess_model(self):
        return self.prompt_for_question_preprocess_model_

    @property
    def text_context_length(self):
        return self.text_content_length_


cfg = Config()