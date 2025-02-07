from typing import List, Dict, Any

async def parse_usage(usage: Any) -> Dict[str, Any]:
    """
    Parse usage information from OpenAI's response.
    This is a common utility used by both streaming and non-streaming responses.


    Args:
        usage: The usage object from OpenAI's response

    Returns:
        Dict containing parsed usage information
    """
    completion_usage = getattr(usage, 'completion_tokens', 0)
    prompt_usage = getattr(usage, 'prompt_tokens', 0)
    
    completion_tokens_details = getattr(usage, 'completion_tokens_details', None)
    reasoning_usage = getattr(completion_tokens_details, 'reasoning_tokens', 0) if completion_tokens_details else 0

    usage_info = {
        "usage": {
            "completion_usage": completion_usage,
            "prompt_usage": prompt_usage,
            "reasoning_usage": reasoning_usage
        }
    }

    return usage_info 

async def parse_usage_gemini(usage: Any) -> Dict[str, Any]:
    """
    Parse usage information from Gemini's response.
    """
    completion_usage = getattr(usage, 'candidates_token_count', 0)
    prompt_usage = getattr(usage, 'prompt_token_count', 0)

    reasoning_usage = getattr(usage, 'reasoning_token_count', 0)

    usage_info = {
        "usage": {
            "completion_usage": completion_usage,
            "prompt_usage": prompt_usage,
            "reasoning_usage": reasoning_usage
        }
    }
    return usage_info

