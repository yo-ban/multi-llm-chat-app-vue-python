import os
import base64
from io import BytesIO
from PIL import Image
import google.generativeai as genai
from typing import List, Dict, Any

async def upload_image_to_gemini(image_data: str, mime_type: str) -> Any:
    """
    Upload an image to Gemini API
    
    Args:
        image_data: Base64 encoded image data
        mime_type: MIME type of the image
        
    Returns:
        Uploaded image object from Gemini
    """
    image = Image.open(BytesIO(base64.b64decode(image_data)))
    buffer = BytesIO()
    image.save(buffer, format=mime_type.split('/')[1])
    file_path = f'temp_image.{mime_type.split("/")[1]}'
    
    try:
        with open(file_path, 'wb') as f:
            f.write(buffer.getvalue())
        uploaded_file = genai.upload_file(file_path, mime_type=mime_type)
        return uploaded_file
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

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