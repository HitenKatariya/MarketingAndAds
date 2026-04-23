import os
import sys
sys.path.insert(0, 'D:/ai_project/backend')

from core.config import get_hf_api_key
api_key = get_hf_api_key()
os.environ['HF_TOKEN'] = api_key
print(f'HF_TOKEN set: {bool(api_key)}')
print('Downloading models...')

from transformers import AutoTokenizer, AutoModelForCausalLM, T5Tokenizer, T5ForConditionalGeneration

print('Downloading Mistral tokenizer...')
tokenizer = AutoTokenizer.from_pretrained('mistralai/Mistral-7B-Instruct-v0.3')
print('Mistral tokenizer done')

print('Downloading Mistral model (this may take a while)...')
model = AutoModelForCausalLM.from_pretrained('mistralai/Mistral-7B-Instruct-v0.3')
print('Mistral model done')

print('Downloading FLAN-T5...')
t5_tokenizer = T5Tokenizer.from_pretrained('google/flan-t5-base')
t5_model = T5ForConditionalGeneration.from_pretrained('google/flan-t5-base')
print('FLAN-T5 done')

print('All models downloaded successfully!')
