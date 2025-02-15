from typing import List, Dict, Any
from google.genai import types

# Constants for Web Search Tool
WEB_SEARCH_TOOL_DESCRIPTION = (
    "Perform a targeted web search to retrieve relevant URLs along with concise snippets. "
    "Use this tool when you need to discover new information, verify facts, or gather current data. "
)

WEB_SEARCH_TOOL_PARAMETERS_DESCRIPTION = {
    "query": "The information is extracted and made into a query, focusing on the **information to be obtained from the web** that is necessary to answer the question, rather than the final answer required by the user.",
    "num_results": "The number of results to return from the search."
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

def get_tool_definitions(without_human_fallback: bool = False) -> List[Dict[str, Any]]:
    """
    Get all function definitions for OpenAI function calling.
    Centralizes all tool definitions in one place for better maintainability.

    Returns:
        List[Dict[str, Any]]: A list of tool definitions in OpenAI function calling format.
    """
    # Web Search Tool
    web_search_tool = {
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
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            },
            "strict": False
        }
    }
    # Web Browsing Tool
    web_browsing_tool = {
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
    # Need-Asking-Human Tool (Fallback)
    need_ask_human_tool = {
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
    tool_definitions = [web_search_tool, web_browsing_tool]
    if not without_human_fallback:
        tool_definitions.append(need_ask_human_tool)
    return tool_definitions

def get_gemini_tool_definitions(without_human_fallback: bool = False) -> List[types.Tool]:
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

    tool_definitions = [web_search_function, web_browsing_function]

    if not without_human_fallback:
        tool_definitions.append(need_ask_human_function)

    return tool_definitions