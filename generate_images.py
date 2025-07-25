import os
import requests
from openai import OpenAI
import sys
from pathlib import Path

# Set OpenAI API key - use environment variable or prompt user
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("Please set OPENAI_API_KEY environment variable")
    sys.exit(1)

client = OpenAI(api_key=api_key)

def generate_and_save_image(prompt, filename):
    """Generate an image using DALL-E 3 and save it locally"""
    try:
        print(f"Generating image: {filename}")
        
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        image_url = response.data[0].url
        
        # Download the image
        img_response = requests.get(image_url)
        if img_response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(img_response.content)
            print(f"[OK] Saved {filename}")
        else:
            print(f"[ERROR] Failed to download {filename}")
            
    except Exception as e:
        print(f"[ERROR] Error generating {filename}: {str(e)}")

# Define images to generate
images_to_generate = [
    {
        "prompt": "Professional portrait photo of a skateboarder in his 50s with short hair, friendly smile, wearing casual skateboarding attire, clean studio lighting, high quality portrait photography",
        "filename": "tony-hawk-portrait.jpg"
    },
    {
        "prompt": "Dynamic action shot of a professional skateboarder performing an aerial spin trick (900) on a halfpipe ramp, dramatic lighting, motion blur, X-Games style photography, crowd in background",
        "filename": "tony-hawk-900.jpg"
    },
    {
        "prompt": "Wide angle photo of a modern concrete skatepark with ramps, rails and bowls, blue sky, professional skateboarder in the distance, architectural photography style",
        "filename": "tony-hawk-skatepark.jpg"
    }
]

# Generate all images
for img in images_to_generate:
    generate_and_save_image(img["prompt"], img["filename"])

print("\nAll images generated!")