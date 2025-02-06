import os
import base64
from io import BytesIO
from PIL import Image
from google import genai
from google.genai.types import File
from typing import List, Dict, Any

async def upload_image_to_gemini(image_data: str, mime_type: str) -> File:
    """
    Upload an image to Gemini API using the new client
    
    Args:
        image_data: Base64 encoded image data
        mime_type: MIME type of the image
        
    Returns:
        Uploaded file object from Gemini
    """
    # Decode base64 image data to bytes
    image_bytes = base64.b64decode(image_data)
    
    # Create BytesIO object for the image
    image_buffer = BytesIO(image_bytes)
    
    # Upload directly from BytesIO without saving to disk
    try:
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        uploaded_file = client.files.upload(
            file=image_buffer,
            config={"mime_type": mime_type}
        )
        return uploaded_file
    except Exception as e:
        raise ValueError(f"Error uploading image to Gemini: {str(e)}")

async def process_images(images: List[str]) -> List[Dict[str, Any]]:
    """
    Process a list of base64 encoded images
    
    Args:
        images: List of base64 encoded image strings
        
    Returns:
        List of processed image content objects
    """
    content = []
    for image in images:
        try:
            media_type = image.split(';')[0].split(':')[1]
            image_data = base64.b64decode(image.split(",")[1])
            image = Image.open(BytesIO(image_data))
            width, height = image.size

            # Resize if image is too large
            if max(width, height) > 1024:
                new_size = (1024, int(height * (1024 / width))) if width > height else (int(width * (1024 / height)), 1024)
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Convert image to bytes
            image_data = BytesIO()
            image.save(image_data, format=media_type.split('/')[1])
            image_data = image_data.getvalue()
            
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "data": base64.b64encode(image_data).decode("utf-8"),
                    "media_type": media_type,
                }
            })
        except Exception as e:
            raise ValueError(f"Error processing image: {str(e)}")
            
    return content 