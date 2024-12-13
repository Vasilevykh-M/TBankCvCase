import PIL

import torch

import diffusers

from transformers import AutoTokenizer, CLIPImageProcessor, CLIPVisionModel

from llava.model import *
from llava.conversation import conv_templates

from mgie_llava import LlavaLlamaForCausalLM

from config import *

from PIL import Image, ImageOps
import numpy as np


def remove_alter(s):
    if 'ASSISTANT:' in s: 
        s = s[s.index('ASSISTANT:')+10:].strip()
    if '</s>' in s: 
        s = s[:s.index('</s>')].strip()
    if 'alternative' in s.lower(): 
        s = s[:s.lower().index('alternative')]
    if '[IMG0]' in s: 
        s = s[:s.index('[IMG0]')]
    s = '.'.join([s.strip() for s in s.split('.')[:2]])
    if s[-1]!='.': 
        s += '.'
    return s.strip()


class MGIE_Model():
    def __init__(
            self,
            path_llava=PATH_LLAVA,
            path_mllm=PATH_MLLM, 
            path_unet=PATH_UNET, 
            path_pix2pix=PATH_PIX2PIX,
            device=DEVICE
    ):
        self.tokenizer = AutoTokenizer.from_pretrained(path_llava)
        self.tokenizer.padding_side = 'left'
        self.tokenizer.add_tokens(SPECIAL_TOKENS, special_tokens=True)

        self.model = LlavaLlamaForCausalLM.from_pretrained(
            path_llava, 
            low_cpu_mem_usage=True, 
            torch_dtype=torch.float16, 
            use_cache=True
        ).to(device)

        self.image_processor = CLIPImageProcessor.from_pretrained(
            self.model.config.mm_vision_tower, 
            torch_dtype=torch.float16
        )

        self.model.resize_token_embeddings(len(self.tokenizer))

        ckpt = torch.load(path_mllm, map_location='cpu')
        self.model.load_state_dict(ckpt, strict=False)
        mm_use_im_start_end = getattr(self.model.config, 'mm_use_im_start_end', False)

        self.tokenizer.add_tokens([DEFAULT_IMAGE_PATCH_TOKEN], special_tokens=True)
        if mm_use_im_start_end: 
            self.tokenizer.add_tokens([DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN], special_tokens=True)

        self.vision_tower = self.model.get_model().vision_tower[0]
        self.vision_tower = CLIPVisionModel.from_pretrained(
            self.vision_tower.config._name_or_path, 
            torch_dtype=torch.float16, 
            low_cpu_mem_usage=True
        ).to(device)

        self.model.get_model().vision_tower[0] = self.vision_tower

        self.vision_config = self.vision_tower.config
        self.vision_config.im_patch_token = self.tokenizer.convert_tokens_to_ids([DEFAULT_IMAGE_PATCH_TOKEN])[0]
        self.vision_config.use_im_start_end = mm_use_im_start_end
        if mm_use_im_start_end: 
            self.vision_config.im_start_token, self.vision_config.im_end_token = self.tokenizer.convert_tokens_to_ids([DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN])

        self.image_token_len = (self.vision_config.image_size // self.vision_config.patch_size) ** 2

        self.model.eval()

        self.embedding = ckpt['emb'].to(device)
        with torch.inference_mode(): 
            self.null_embedding = self.model.edit_head(torch.zeros(1, 8, 4096).half().to(device), self.embedding)

        self.pipeline = diffusers.StableDiffusionInstructPix2PixPipeline.from_pretrained(
            path_pix2pix, 
            torch_dtype=torch.float16, 
            safety_checker=None
        ).to(device)
        self.pipeline.set_progress_bar_config(disable=True)
        self.pipeline.unet.load_state_dict(torch.load(path_unet, map_location='cpu'))


    def generate_image(self, image: PIL.Image, prompt: str, device="cuda", seed=42):
        image_pixel_values = self.image_processor(image, return_tensors="pt")["pixel_values"]
        image_pixel_values = image_pixel_values.half()

        prompt = BASIC_PROMPT \
                + prompt \
                + "\n" \
                + DEFAULT_IM_START_TOKEN \
                + DEFAULT_IMAGE_PATCH_TOKEN * self.image_token_len \
                + DEFAULT_IM_END_TOKEN

        conv = conv_templates['vicuna_v1_1'].copy()
        conv.append_message(conv.roles[0], prompt)
        conv.append_message(conv.roles[1], None)
        prompt = conv.get_prompt()
        prompt = self.tokenizer(prompt)
        prompt_input_ids = torch.as_tensor(prompt['input_ids']).unsqueeze(dim=0)
        prompt_attn_mask = torch.as_tensor(prompt['attention_mask']).unsqueeze(dim=0)
        
        with torch.inference_mode():
            out = self.model.generate(
                prompt_input_ids.to(device), 
                images=image_pixel_values.to(device), 
                attention_mask=prompt_attn_mask.to(device), 
                do_sample=False, 
                max_new_tokens=96, 
                num_beams=1, 
                no_repeat_ngram_size=3, 
                return_dict_in_generate=True, 
                output_hidden_states=True
            )
            hid = torch.cat([x[-1] for x in out['hidden_states']], dim=1)[0]
            out = out['sequences'][0].tolist()
            
            p = min(out.index(32003)-1 if 32003 in out else len(hid)-9, len(hid)-9)
            hid = hid[p:p+8]

            out = remove_alter(self.tokenizer.decode(out))
            emb = self.model.edit_head(hid.unsqueeze(dim=0), self.embedding)
            result_image = self.pipeline(
                image=image,
                prompt_embeds=emb,
                negative_prompt_embeds=self.null_embedding,
                guidance_scale=7.5, image_guidance_scale=1.5
            ).images[0]

        return result_image

