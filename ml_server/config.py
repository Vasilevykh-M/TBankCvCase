UPLOAD_FOLDER = 'uploads'
context_length = 3

ml_server_url = "http://localhost:8000/v1/chat/completions"



prompt_for_question_preprocess_model = """Extract only the information about what modifications or changes the user wants to make to the image from the text below. Exclude any irrelevant text and focus solely on the specific requests for adjustments.
Text: '{}'"""


prompt_for_choosing_image = """You are a model designed to assist an image generator in understanding which image the user wants to modify. Three images have already been generated in the following order: image1, image2, and image3, with image3 being the most recently created. Analyze the user's request: {}, and determine which of these images they want to use. Respond with one of the following options: [image1, image2, image3]."""