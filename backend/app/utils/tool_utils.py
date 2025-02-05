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
                "description": (
                    "Perform a targeted web search for the most up-to-date information. "
                    "Use this tool when the user explicitly requests recent information or when the query indicates "
                    "that the required details are newer than your current knowledge base. "
                    "This ensures that live data is fetched when static information might be outdated."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "The search query used to fetch up-to-date information. "
                                "The query takes into account the language of the questioner."
                            )
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
                "description": (
                    "Extract and analyze detailed information from a specified webpage. "
                    "Use this tool when search results or explicit user instructions indicate that a deeper investigation "
                    "of the webpage content is required. It leverages Gemini's visual and text analysis capabilities to provide comprehensive insights."
                ),
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