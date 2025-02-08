from typing import List, Dict, Any
from google.genai import types

# Constants for Web Search Tool
WEB_SEARCH_TOOL_DESCRIPTION = (
    "Perform a targeted web search to retrieve relevant URLs along with concise snippets. "
    "Use this tool when you need to discover new information, verify facts, or gather current data. "
)

WEB_SEARCH_TOOL_PARAMETERS_DESCRIPTION = {
    "query": "A concise, well-crafted search query that reflects the precise information needed. Avoid copying the entire user request verbatim; focus on the key concepts you need to explore or verify.",
    "num_results": "Number of search results to return, default is 5",
}

# Constants for Web Browsing Tool
WEB_BROWSING_TOOL_DESCRIPTION = (
    "Perform an interactive web browsing session on a given URL to investigate its content in detail. "
    "Use this after identifying a promising link (either provided by the user or found via the Web Search Tool) "
    "to obtain comprehensive information, verify context, or extract specific data (e.g., code snippets, instructions, logs, etc.)."
)

WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION = {
    "url": "The URL of the webpage to extract information from. Must be a valid HTTP/HTTPS URL.",
    "query": (
        "A targeted request for the information you need to extract. "
        "Focus on what specific details (code snippets, instructions, data, context) will help you answer the user's question comprehensively."
    ),
}

# Constants for Need-Asking-Human Tool (Fallback)
NEED_ASK_HUMAN_TOOL_DESCRIPTION = (
    "A tool that requests confirmation or clarification from the user when web-related tools should not be automatically invoked. "
    "Use this tool for cases such as casual greetings or when the user's query is contains ambiguous or does not provide enough detail."
)
NEED_ASK_HUMAN_TOOL_PARAMETERS_DESCRIPTION = {
    "clarification_points": (
        "An array of detailed and specific prompts for follow-up questions to ask the user. "
        "which is a list of specific follow-up questions addressing multiple "
        "aspects that the user might be interested in—for example, the desired scope, timeframe, context, or specific data points."
    )
}

def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get all function definitions for OpenAI function calling.
    Centralizes all tool definitions in one place for better maintainability.

    Returns:
        List[Dict[str, Any]]: A list of tool definitions in OpenAI function calling format.
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
        # Web Browsing Tool
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
        },
        # Need-Asking-Human Tool (Fallback)
        {
            "type": "function",
            "function": {
                "name": "need_ask_human",
                "description": NEED_ASK_HUMAN_TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "clarification_points": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": NEED_ASK_HUMAN_TOOL_PARAMETERS_DESCRIPTION["clarification_points"]
                        }
                    },
                    "required": ["clarification_points"],
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
        List[types.Tool]: A list of tool definitions in Gemini API format.
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

    # Need-Asking-Human Tool Definition for Gemini API
    need_ask_human_function = types.FunctionDeclaration(
        name="need_ask_human",
        description=NEED_ASK_HUMAN_TOOL_DESCRIPTION,
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "clarification_points": types.Schema(
                    type="ARRAY",
                    items=types.Schema(
                        type="STRING",
                    ),
                    description=NEED_ASK_HUMAN_TOOL_PARAMETERS_DESCRIPTION["clarification_points"],
                )
            },
            required=["clarification_points"],
        ),
    )


    # Create Tool objects for each function
    web_search_tool = types.Tool(function_declarations=[web_search_function])
    web_browsing_tool = types.Tool(function_declarations=[web_browsing_function])
    need_ask_human_tool = types.Tool(function_declarations=[need_ask_human_function])

    return [web_search_tool, web_browsing_tool, need_ask_human_tool]
