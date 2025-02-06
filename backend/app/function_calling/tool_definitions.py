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
                    "Perform a targeted web search to retrieve relevant URLs along with concise snippets "
                    "that provide a brief summary of the content. Use this tool when the user requires timely information "
                    "coupled with direct links for quick reference and further investigation."
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
                "name": "web_browsing",
                "description": (
                    "Perform an interactive web browsing session on a given URL to investigate its content in detail. "
                    "After a web search provides the URL, use this tool to explore the webpage further and gather comprehensive information "
                    "that supports the user's query."
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