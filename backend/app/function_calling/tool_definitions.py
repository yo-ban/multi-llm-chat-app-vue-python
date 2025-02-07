from typing import List, Dict, Any
from google.genai import types

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
        description=(
            "Perform a targeted web search to retrieve relevant URLs along with concise snippets "
            "that provide a brief summary of the content. Use this tool when the user requires timely information "
            "coupled with direct links for quick reference and further investigation."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "query": types.Schema(
                    type="STRING",
                    description=(
                        "The search query used to fetch up-to-date information. "
                        "The query takes into account the language of the questioner."
                    ),
                ),
                "num_results": types.Schema(
                    type="INTEGER",
                    description="Number of search results to return, default is 5",
                ),
            },
            required=["query"],
        ),
    )

    # Web Browsing Tool Definition
    web_browsing_function = types.FunctionDeclaration(
        name="web_browsing",
        description=(
            "Perform an interactive web browsing session on a given URL to investigate its content in detail. "
            "After a web search provides the URL, use this tool to explore the webpage further and gather comprehensive information "
            "that supports the user's query."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "url": types.Schema(
                    type="STRING",
                    description="The URL of the webpage to extract information from. Must be a valid HTTP/HTTPS URL.",
                ),
                "query": types.Schema(
                    type="STRING",
                    description="The specific information or analysis you want to extract from the webpage. Be precise and clear about what information you're looking for.",
                ),
            },
            required=["url", "query"],
        ),
    )

    # Create Tool objects for each function
    web_search_tool = types.Tool(function_declarations=[web_search_function])
    web_browsing_tool = types.Tool(function_declarations=[web_browsing_function])

    return [web_search_tool, web_browsing_tool]

def get_gemini_config(tools: List[types.Tool] = None) -> types.GenerateContentConfig:
    """
    Get the default configuration for Gemini API function calling.

    Args:
        tools (List[types.Tool], optional): List of tools to include in the configuration.

    Returns:
        types.GenerateContentConfig: Configuration for Gemini API
    """
    return types.GenerateContentConfig(
        tools=tools,
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode='AUTO')
        ),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=10  # デフォルトの最大リモート呼び出し回数
        ),
        temperature=0.7,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
    ) 