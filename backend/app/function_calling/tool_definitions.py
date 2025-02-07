from typing import List, Dict, Any
from google.genai import types


WEB_SEARCH_TOOL_DESCRIPTION = (
    "Perform a targeted web search to retrieve relevant URLs along with concise snippets "
    "that provide a brief summary of the content. Use this tool when the user requires timely information "
    "coupled with direct links for quick reference and further investigation."
)

WEB_SEARCH_TOOL_PARAMETERS_DESCRIPTION = (
    {
        "query": "The search query used to fetch up-to-date information. The query takes into account the language of the questioner.",
        "num_results": "Number of search results to return, default is 5",
    }
)

WEB_BROWSING_TOOL_DESCRIPTION = (
    "Perform an interactive web browsing session on a given URL to investigate its content in detail. "
    "After a web search provides the URL, use this tool to explore the webpage further and gather comprehensive information "
    "that supports the user's query."
)

WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION = (
    {
        "url": "The URL of the webpage to extract information from. Must be a valid HTTP/HTTPS URL.",
        "query": "The specific information or analysis you want to extract from the webpage. Be precise and clear about what information you're looking for.",
    }
)


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
                "description": WEB_SEARCH_TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": WEB_SEARCH_TOOL_PARAMETERS_DESCRIPTION["query"]
                        },
                        "num_results": {
                            "type": "integer",
                            "description": WEB_SEARCH_TOOL_PARAMETERS_DESCRIPTION["num_results"],
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
                "description": WEB_BROWSING_TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION["url"]
                        },
                        "query": {
                            "type": "string",
                            "description": WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION["query"]
                        }
                    },
                    "required": ["url", "query"],
                    "additionalProperties": False
                },
                "strict": False
            }
        }
    ]

def get_gemini_tool_definitions() -> List[types.Tool]:
    """
    Get all function definitions for Gemini API function calling.
    Centralizes all tool definitions in one place for better maintainability.

    Returns:
        List[types.Tool]: A list of tool definitions in Gemini API format
    """
    # Web Search Tool Definition
    web_search_function = types.FunctionDeclaration(
        name="web_search",
        description=WEB_SEARCH_TOOL_DESCRIPTION,
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "query": types.Schema(
                    type="STRING",
                    description=WEB_SEARCH_TOOL_PARAMETERS_DESCRIPTION["query"],
                ),
                "num_results": types.Schema(
                    type="INTEGER",
                    description=WEB_SEARCH_TOOL_PARAMETERS_DESCRIPTION["num_results"],
                ),
            },
            required=["query"],
        ),
    )

    # Web Browsing Tool Definition
    web_browsing_function = types.FunctionDeclaration(
        name="web_browsing",
        description=WEB_BROWSING_TOOL_DESCRIPTION,
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "url": types.Schema(
                    type="STRING",
                    description=WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION["url"],
                ),
                "query": types.Schema(
                    type="STRING",
                    description=WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION["query"],
                ),
            },
            required=["url", "query"],
        ),
    )

    # Create Tool objects for each function
    web_search_tool = types.Tool(function_declarations=[web_search_function])
    web_browsing_tool = types.Tool(function_declarations=[web_browsing_function])

    return [web_search_tool, web_browsing_tool]
