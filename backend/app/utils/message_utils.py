from typing import List, Dict, Any
from app.models.models import Message
from app.utils.image_utils import process_images

async def prepare_api_messages(messages: List[Message]) -> List[Dict[str, Any]]:
    """
    Prepare messages for API consumption
    
    Args:
        messages: List of Message objects
        
    Returns:
        List of formatted messages ready for API consumption
    """
    api_messages = []
    for message in messages:
        content = await process_images(message.images or [])
        if message.text:
            content.append({"type": "text", "text": message.text})
        else:
            content.append({"type": "text", "text": "Please describe this image(s)."})
        api_messages.append({"role": message.role, "content": content})
    return api_messages

def prepare_openai_messages(system_message: str, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
            elif item['type'] == 'image':
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{item['source']['media_type']};base64,{item['source']['data']}"
                    }
                })
        openai_messages.append({"role": msg['role'], "content": content})
    
    return openai_messages

def prepare_anthropic_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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