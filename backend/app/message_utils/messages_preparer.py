from typing import List, Dict, Any
from app.models.models import Message
from app.misc_utils.image_utils import process_images
from app.logger.logging_utils import log_info

async def prepare_api_messages(messages: List[Message], multimodal: bool = False) -> List[Dict[str, Any]]:
    """
    Prepare messages for API consumption
    
    Args:
        messages: List of Message objects
        multimodal: Whether to include image content in messages
        
    Returns:
        List of formatted messages ready for API consumption
    """
    api_messages = []
    for message in messages:
        content = []
        if multimodal and message.images:
            content.extend(await process_images(message.images))
        if message.text:
            content.append({"type": "text", "text": message.text})
        else:
            # Only add default text for image description if multimodal is enabled and there are images
            if multimodal and message.images:
                content.append({"type": "text", "text": "Please describe this image(s)."})
            else:
                content.append({"type": "text", "text": ""})  # Empty text if no content
        api_messages.append({"role": message.role, "content": content})
    return api_messages

async def prepare_openai_messages(system_message: str, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prepare messages specifically for OpenAI API format
    

    Args:
        system_message: System message to prepend
        messages: List of message dictionaries
        
    Returns:
        List of messages formatted for OpenAI API
    """
    openai_messages = [{"role": "system", "content": system_message}]
    
    for msg in messages:
        content = []
        for item in msg['content']:
            if item['type'] == 'text':
                content.append({"type": "text", "text": item['text']})
            if item['type'] == 'image':
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{item['source']['media_type']};base64,{item['source']['data']}"
                    }
                })
        openai_messages.append({"role": msg['role'], "content": content})
    
    return openai_messages

async def prepare_anthropic_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prepare messages specifically for Anthropic API format
    

    Args:
        messages: List of message dictionaries
        
    Returns:
        List of messages formatted for Anthropic API
    """
    return [
        {
            "role": msg["role"],
            "content": msg["content"]
        }
        for msg in messages
    ] 
