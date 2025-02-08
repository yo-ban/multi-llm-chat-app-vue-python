from typing import List, Dict, Any
from google.genai import types

# Constants for Web Search Tool
WEB_SEARCH_TOOL_DESCRIPTION = (
    "Perform a targeted web search to retrieve relevant URLs along with concise snippets "
    "that provide a brief summary of the content. Use this tool when the user requires timely information "
    "coupled with direct links for quick reference and further investigation."
)
WEB_SEARCH_TOOL_PARAMETERS_DESCRIPTION = {
    "query": "The search query used to fetch up-to-date information. The query takes into account the language of the questioner.",
    "num_results": "Number of search results to return, default is 5",
}

# Constants for Web Browsing Tool
WEB_BROWSING_TOOL_DESCRIPTION = (
    "Perform an interactive web browsing session on a given URL to investigate its content in detail. "
    "After a web search provides the URL, use this tool to explore the webpage further and gather comprehensive information "
    "that supports the user's query."
)
WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION = {
    "url": "The URL of the webpage to extract information from. Must be a valid HTTP/HTTPS URL.",
    "query": "The specific information or analysis you want to extract from the webpage. Be precise and clear about what information you're looking for.",
}

# Constants for Need-Asking-Human Tool (Fallback)
NEED_ASK_HUMAN_TOOL_DESCRIPTION = (
    "A tool that requests confirmation or clarification from the user when web-related tools should not be automatically invoked. "
    "Use this tool for cases such as casual greetings or when the user's query is contains ambiguous or does not provide enough detail."
    "It requires a parameter 'clarification_points', which is a list of specific follow-up questions addressing multiple "
    "aspects that the user might be interested in—for example, the desired scope, timeframe, context, or specific data points. "
    "These prompts help pinpoint what additional information is needed."
)
NEED_ASK_HUMAN_TOOL_PARAMETERS_DESCRIPTION = {
    "clarification_points": (
        "An array of detailed and specific prompts for follow-up questions to ask the user. "
        "These should capture aspects such as: "
        "1) Which specific data or outcome are you interested in? "
        "2) Can you specify a timetable or context for this query? "
        "3) Are there particular details or examples you require? "
        "Include as many prompts as needed to fully clarify the user's information needs."
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
