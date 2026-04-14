import os
from huggingface_hub import InferenceClient
from io import BytesIO

# Get API key
from core.config import get_hf_api_key
api_key = get_hf_api_key()
print(f'API Key: {bool(api_key)}')

# Test different providers for different tasks
providers_to_try = [
    "nscale",
    "hf-inference", 
    "auto",
    "together",
]

print('\n=== Testing Image Generation (nscale) ===')
try:
    client = InferenceClient(
        provider="nscale",
        api_key=api_key,
    )
    
    image = client.text_to_image(
        prompt="A beautiful sunset over mountains, high quality",
        model="stabilityai/stable-diffusion-xl-base-1.0",
    )
    print(f'Image type: {type(image)}')
    
    # Save image
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    with open("test_sdxl.png", "wb") as f:
        f.write(buffer.getvalue())
    print(f'Image saved! Size: {len(buffer.getvalue())} bytes')
except Exception as e:
    print(f'Image Error: {e}')
    import traceback
    traceback.print_exc()

print('\n=== Testing Text Generation ===')
# Try different providers for text
for provider in providers_to_try:
    print(f'\nTrying provider: {provider}')
    try:
        client = InferenceClient(
            provider=provider,
            api_key=api_key,
        )
        
        # Try conversational task which nscale supports
        try:
            response = client.conversational(
                model="mistralai/Mistral-7B-Instruct-v0.3",
                text="Say hello in one word",
            )
            print(f'Conversational result: {response}')
        except Exception as conv_e:
            print(f'Conversational error: {conv_e}')
            
    except Exception as e:
        print(f'Provider error: {e}')
