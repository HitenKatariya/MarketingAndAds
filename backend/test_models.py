import asyncio
import httpx
from core.config import get_hf_api_key

async def test_with_provider():
    api_key = get_hf_api_key()
    print(f'API Key: {bool(api_key)}')
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'X-Provider': 'nscale',
    }
    
    models = [
        ('FLAN-T5 Base', 'google/flan-t5-base', 'text'),
        ('Mistral', 'mistralai/Mistral-7B-Instruct-v0.3', 'text'),
        ('SDXL', 'stabilityai/stable-diffusion-xl-base-1.0', 'image'),
    ]
    
    for name, model_id, model_type in models:
        print(f'\n=== Testing {name} ({model_id}) ===')
        
        urls = [
            f'https://router.huggingface.co/hf-inference/models/{model_id}',
            f'https://router.huggingface.co/{model_id}',
        ]
        
        for url in urls:
            print(f'\nURL: {url}')
            
            if model_type == 'text':
                payload = {'inputs': 'Say hello in one word', 'parameters': {'max_new_tokens': 5}}
            else:
                payload = {'inputs': 'A beautiful sunset over mountains'}
            
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    print(f'Status: {response.status_code}')
                    ct = response.headers.get('content-type', '')
                    print(f'Content-Type: {ct}')
                    
                    if response.status_code == 200:
                        if 'image' in ct:
                            print(f'IMAGE! Size: {len(response.content)} bytes')
                            # Save image
                            with open(f'test_{name.replace(" ", "_").lower()}.png', 'wb') as f:
                                f.write(response.content)
                            print('Image saved!')
                        else:
                            print(f'Response: {response.json()}')
                        break
                    elif response.status_code == 503:
                        data = response.json()
                        wait = data.get('estimated_time', 10)
                        print(f'Loading... wait {wait}s')
                    elif response.status_code == 410:
                        print(f'Deprecated: {response.json()}')
                    elif response.status_code == 404:
                        print('Not found')
                    else:
                        print(f'Error: {response.text[:100]}')
                        
            except Exception as e:
                print(f'Error: {e}')

if __name__ == '__main__':
    asyncio.run(test_with_provider())
