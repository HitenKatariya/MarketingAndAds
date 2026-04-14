import asyncio
from core.huggingface_client import hf_client

async def test():
    print("Testing HF Client...")
    print(f"Configured: {hf_client.is_configured}")
    print(f"Text model loaded: {hf_client.text_model is not None}")
    print(f"Diagnostics: {hf_client.diagnostics()}")

    # Test text generation
    print("\n=== Testing Text Generation ===")
    text_result = await hf_client.generate_text(
        "Create a marketing caption for pizza",
        model_id="google/flan-t5-base",
        max_new_tokens=50
    )
    print(f"Text result: {text_result}")

    # Test image generation
    print("\n=== Testing Image Generation ===")
    image_bytes = await hf_client.generate_image(
        "A delicious pizza with cheese",
        model_id="stabilityai/stable-diffusion-xl-base-1.0",
        width=512,
        height=512
    )
    print(f"Image bytes: {len(image_bytes)}")

    # Save image
    with open("test_output.png", "wb") as f:
        f.write(image_bytes)
    print("Image saved to test_output.png")

    print("\n=== Final Diagnostics ===")
    print(hf_client.diagnostics())

if __name__ == '__main__':
    asyncio.run(test())
