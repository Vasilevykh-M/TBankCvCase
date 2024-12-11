import os

from dotenv import load_dotenv
class Config:
    def __init__(self):
        load_dotenv()


        self.UPLOAD_FOLDER_  = os.getenv('UPLOAD_FOLDER')
        self.context_length_ = os.getenv('CONTEXT_LENGHT')

        self.ml_server_url_ = os.getenv('ML_WORKER_PROMT')

        self.prompt_for_question_preprocess_model_ = os.getenv('PROMT_FOR_QUESTION_MODEL')

        self.prompt_for_choosing_image_ = os.getenv('PROMT_FOR_CHOSING_IMAGE')

    def UPLOAD_FOLDER(self):
        return self.UPLOAD_FOLDER_

    def context_length(self):
        return self.context_length_
    
    def ml_server_url(self):
        return self.ml_server_url_
    
    def prompt_for_question_preprocess_model(self):
        return self.prompt_for_question_preprocess_model_

    
    def prompt_for_choosing_image(self):
        return self.prompt_for_choosing_image_
    
cfg = Config()