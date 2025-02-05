from typing import List, Dict, Any

def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get all function definitions for OpenAI function calling.
    Centralizes all tool definitions in one place for better maintainability.

    Returns:
        List[Dict[str, Any]]: A list of tool definitions in OpenAI function calling format
    """
    return [
        # Web Search Tool
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "If you need information that cannot normally be answered, search the web for information. If a user's question includes words such as 「search the web.」 be sure to use this function.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find relevant information. The query is processed by taking into account the language used by the questioner."
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of search results to return, default is 5",
                        }
                    },
                    "required": ["query"],
                    "additionalProperties": False
                },
                "strict": False
            }
        },
        # Web Extraction Tool
        {
            "type": "function",
            "function": {
                "name": "extract_web_site",
                "description": "Extract and analyze information from a specified webpage using Gemini's visual and text analysis capabilities. Use this when you need to extract specific information from a webpage or analyze its content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL of the webpage to extract information from. Must be a valid HTTP/HTTPS URL."
                        },
                        "query": {
                            "type": "string",
                            "description": "The specific information or analysis you want to extract from the webpage. Be precise and clear about what information you're looking for."
                        }
                    },
                    "required": ["url", "query"],
                    "additionalProperties": False
                },
                "strict": False
            }
        }
    ] 