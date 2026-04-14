import asyncio
import httpx
from core.config import get_hf_api_key

async def test_hf():
    api_key = get_hf_api_key()
    print(f'API Key: {bool(api_key)}')
    if not api_key:
        print('No API key!')
        return
    
    headers = {
        'Authorization': f'Bearer {api_key}',
    }
    
    # Check HF API documentation for correct endpoint
    # According to latest docs, use the proper inference format
    
    print('\n1. Testing HF Spaces inference (Task API)...')
    # Try using the task-based inference
    tasks = [
        ('text-generation', 'gpt2', {'inputs': 'Hello world'}),
        ('text-to-image', 'stabilityai/stable-diffusion-xl-base-1.0', {'inputs': 'A sunset'}),
    ]
    
    for task, model, payload in tasks:
        print(f'\nTask: {task}, Model: {model}')
        url = f'https://router.huggingface.co/{model}'
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                print(f'  Status: {response.status_code}')
                ct = response.headers.get('content-type', '')
                
                if response.status_code == 200:
                    if 'image' in ct:
                        print(f'  IMAGE! Size: {len(response.content)}')
                    else:
                        print(f'  Response: {str(response.json())[:200]}')
                else:
                    print(f'  {response.text[:200]}')
        except Exception as e:
            print(f'  Error: {e}')
    
    print('\n\n2. Testing alternative format with explicit inference...')
    # Try with explicit inference endpoint
    alt_urls = [
        'https://router.huggingface.co/huggingface/clip-vit-large-patch14',
        'https://router.huggingface.co/mistralai/Mistral-7B-Instruct-v0.2',
    ]
    
    for url in alt_urls:
        print(f'\n{url}')
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url, 
                    headers=headers, 
                    json={'inputs': 'test'}
                )
                print(f'Status: {response.status_code}')
                if response.status_code == 200:
                    print(f'Success!')
                else:
                    print(response.text[:150])
        except Exception as e:
            print(f'Error: {e}')

if __name__ == '__main__':
    asyncio.run(test_hf())
