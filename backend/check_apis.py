# Check alternative API options
import os

print('Checking API options...')
print(f'REPLICATE_API_TOKEN: {bool(os.environ.get("REPLICATE_API_TOKEN"))}')
print(f'OPENAI_API_KEY: {bool(os.environ.get("OPENAI_API_KEY"))}')

# Check replicate
try:
    import replicate
    print('Replicate package: Available')
except ImportError:
    print('Replicate package: Not available')

# Check openai
try:
    import openai
    print('OpenAI package: Available')
except ImportError:
    print('OpenAI package: Not available')

print('\nChecking HF model access...')
import httpx
from core.config import get_hf_api_key

async def check_hf():
    api_key = get_hf_api_key()
    headers = {'Authorization': f'Bearer {api_key}'}
    
    # Check if token has inference access
    url = 'https://huggingface.co/api/whoami-v2'
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f'User: {data.get("name", "unknown")}')
                print(f'Org: {data.get("org", "none")}')
                print(f'Full Response: {data}')
            else:
                print(f'Auth failed: {response.status_code}')
    except Exception as e:
        print(f'Error: {e}')

import asyncio
asyncio.run(check_hf())
