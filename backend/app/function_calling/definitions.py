from typing import List, Dict, Any, Optional, Callable, get_type_hints, Union, overload, Literal, TypedDict
from google.genai import types
import inspect
import importlib
import asyncio
from functools import lru_cache
import os
import pkgutil

# Import tool functions from the new tools subdirectory
from app.function_calling.tools.web_search_tool import web_search
from app.function_calling.tools.web_browsing_tool import web_browsing
from app.function_calling.tools.request_clarification_tool import request_clarification

from poly_mcp_client.models import CanonicalToolDefinition # 型ヒントのため

# Path to the tools directory
TOOLS_DIR = os.path.dirname(__file__) + '/tools'

@lru_cache(maxsize=1) # Cache the result since directory scanning can be slow
def get_available_tools() -> List[Callable]:
    """
    Dynamically discover and import available tool functions from the 'tools' directory.
    Assumes each .py file in 'tools' defines one tool function with the same name as the file.

    Returns:
        List[Callable]: A list of callable tool functions
    """
    available_tools = []
    # Use pkgutil to find modules in the tools directory
    for _, module_name, _ in pkgutil.iter_modules([TOOLS_DIR]):
        try:
            # Dynamically import the module
            module_path = f"app.function_calling.tools.{module_name}"
            module = importlib.import_module(module_path)
            
            # Assume the function name matches the module name
            function_name = module_name.replace('_tool', '') # Handle potential _tool suffix
            if hasattr(module, function_name):
                func = getattr(module, function_name)
                if callable(func) and inspect.iscoroutinefunction(func):
                    available_tools.append(func)
                else:
                    # Optionally log a warning if a non-callable or non-async function is found
                    print(f"Warning: Found non-async/callable '{function_name}' in {module_path}, skipping.")
            else:
                # Fallback: check if function name includes _tool suffix
                function_name_with_suffix = module_name
                if hasattr(module, function_name_with_suffix):
                    func = getattr(module, function_name_with_suffix)
                    if callable(func) and inspect.iscoroutinefunction(func):
                        available_tools.append(func)
                    else:
                        print(f"Warning: Found non-async/callable '{function_name_with_suffix}' in {module_path}, skipping.")
                else:
                    print(f"Warning: Could not find function '{function_name}' or '{function_name_with_suffix}' in {module_path}")

        except ImportError as e:
            print(f"Error importing tool module {module_name}: {e}")
            
    return available_tools

def generate_tool_definition(func: Callable) -> Dict[str, Any]:
    """
    Generate a canonical tool definition from a function's docstring and signature.

    Args:
        func: The function to generate a tool definition for

    Returns:
        Dict[str, Any]: A canonical tool definition
    """
    # Get function name
    name = func.__name__

    # Get function docstring
    docstring = inspect.getdoc(func) or ""
    lines = docstring.split('\n')

    # Extract description lines until a section header is found
    description_lines = []
    section_headers = ("Args:", "Arguments:", "Parameters:", "Returns:", "Yields:", "Raises:", "Attributes:")
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith(section_headers):
            break
        description_lines.append(line)

    # Join description lines, removing leading/trailing whitespace and redundant internal whitespace
    description = " ".join("\n".join(description_lines).strip().split())

    # Get function signature
    sig = inspect.signature(func)

    # Build parameters
    parameters = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name == 'self' or param_name == 'cls':
            continue

        param_type = "string"  # Default type
        param_desc = ""

        # Try to get type annotation
        if param.annotation != inspect.Parameter.empty:
            if param.annotation == str:
                param_type = "string"
            elif param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            elif param.annotation == list or getattr(param.annotation, "__origin__", None) == list:
                param_type = "array"
            elif param.annotation == dict or getattr(param.annotation, "__origin__", None) == dict:
                param_type = "object"

        # Extract parameter description from docstring
        # This is a simple implementation that assumes Google-style docstrings
        # More sophisticated parsing would be needed for other docstring styles
        param_pattern = f"{param_name}: "
        param_pattern_alt = f"{param_name} - "

        for line in docstring.split('\n'):
            line = line.strip()
            if line.startswith(param_pattern) or line.startswith(param_pattern_alt):
                param_desc = line.split(param_pattern)[-1].split(param_pattern_alt)[-1].strip()
                break

        # Build parameter definition
        param_def = {
            "type": param_type,
            "description": param_desc
        }

        # For array type, add items definition
        if param_type == "array" and getattr(param.annotation, "__args__", None):
            item_type = param.annotation.__args__[0]
            if item_type == str:
                param_def["items"] = {"type": "string"}
            elif item_type == int:
                param_def["items"] = {"type": "integer"}
            elif item_type == float:
                param_def["items"] = {"type": "number"}
            elif item_type == bool:
                param_def["items"] = {"type": "boolean"}

        parameters[param_name] = param_def

        # Add to required parameters if no default value
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    # Create the canonical tool definition
    tool_def: CanonicalToolDefinition = {
        "name": name,
        "description": description,
        "parameters": parameters,
        "required": required
    }

    return tool_def

def convert_tool_definition_for_vendor(tool_def: Dict[str, Any], vendor: str) -> Dict[str, Any]:
    """
    Convert a canonical tool definition to a vendor-specific format.

    Args:
        tool_def: The canonical tool definition
        vendor: The vendor name (openai, anthropic, gemini)

    Returns:
        Dict[str, Any]: The vendor-specific tool definition
    """
    if vendor == "openai":
        # OpenAI format
        return {
            "type": "function",
            "function": {
                "name": tool_def["name"],
                "description": tool_def["description"],
                "parameters": {
                    "type": "object",
                    "properties": tool_def["parameters"],
                    "required": tool_def["required"],
                    "additionalProperties": False
                },
                "strict": False
            }
        }

    elif vendor == "anthropic":
        # Anthropic format
        return {
            "name": tool_def["name"],
            "description": tool_def["description"],
            "input_schema": {
                "type": "object",
                "properties": tool_def["parameters"],
                "required": tool_def["required"]
            }
        }

    elif vendor == "gemini":
        # Gemini format (using types from google.genai)
        properties = {}
        for param_name, param_def in tool_def["parameters"].items():
            schema_type = "STRING"  # Default

            if param_def["type"] == "string":
                schema_type = "STRING"
            elif param_def["type"] == "integer" or param_def["type"] == "number":
                schema_type = "NUMBER"
            elif param_def["type"] == "boolean":
                schema_type = "BOOLEAN"
            elif param_def["type"] == "array":
                schema_type = "ARRAY"
                items_schema = types.Schema(type="STRING")
                if "items" in param_def:
                    item_type = param_def["items"].get("type", "string")
                    if item_type == "string":
                        items_schema = types.Schema(type="STRING")
                    elif item_type in ["integer", "number"]:
                        items_schema = types.Schema(type="NUMBER")
                    elif item_type == "boolean":
                        items_schema = types.Schema(type="BOOLEAN")

                properties[param_name] = types.Schema(
                    type=schema_type,
                    description=param_def["description"],
                    items=items_schema
                )
                continue
            elif param_def["type"] == "object":
                schema_type = "OBJECT"

            properties[param_name] = types.Schema(
                type=schema_type,
                description=param_def["description"]
            )

        return types.FunctionDeclaration(
            name=tool_def["name"],
            description=tool_def["description"],
            parameters=types.Schema(
                type="OBJECT",
                properties=properties,
                required=tool_def["required"]
            )
        )

    else:
        # OpenAPI形式をデフォルトとする
        return {
            "type": "function",
            "function": {
                "name": tool_def["name"],
                "description": tool_def["description"],
                "parameters": {
                    "type": "object",
                    "properties": tool_def["parameters"],
                    "required": tool_def["required"],
                    "additionalProperties": False
                },
                "strict": False
            }
        }

@overload
def get_tool_definitions(without_human_fallback: bool = False, vendor: Optional[str] = None, mcp_tools: None = None) -> List[Dict[str, Any]]: ...

@overload
def get_tool_definitions(without_human_fallback: bool = False, vendor: Literal["gemini"] = "gemini", mcp_tools: Optional[List[CanonicalToolDefinition]] = None) -> types.Tool: ...

@overload
def get_tool_definitions(without_human_fallback: bool = False, vendor: str = ..., mcp_tools: Optional[List[CanonicalToolDefinition]] = None) -> List[Dict[str, Any]]: ...


def get_tool_definitions(
        without_human_fallback: bool = False, 
        vendor: Optional[str] = None,
        mcp_tools: Optional[List[CanonicalToolDefinition]] = None
) -> Union[List[Dict[str, Any]], types.Tool]:
    """
    Get all function definitions for function calling.
    Merges internal tools with provided MCP tools.

    Args:
        without_human_fallback: Whether to exclude the request_clarification tool
        vendor: The vendor name (openai, anthropic, gemini) to format the definitions for
        mcp_tools: Optional list of canonical tool definitions from MCP servers

    Returns:
        Union[List[Dict[str, Any]], types.Tool]: Tool definitions in the requested format
    """
    # 1. Get internal tool functions
    internal_tool_functions = get_available_tools()

    # 2. Filter internal tools if needed
    if without_human_fallback:
        internal_tool_functions = [f for f in internal_tool_functions if f.__name__ != "request_clarification"]

    # 3. Generate canonical definitions for internal tools
    canonical_defs: List[CanonicalToolDefinition] = [generate_tool_definition(func) for func in internal_tool_functions]

    # 4. Merge with provided MCP tools (if any)
    if mcp_tools:
        # Make sure MCP tools don't have the request_clarification name if filtering
        filtered_mcp_tools = mcp_tools
        if without_human_fallback:
            filtered_mcp_tools = [t for t in mcp_tools if not t['name'].endswith('/request_clarification')] # server_name/tool_name を想定
        canonical_defs.extend(filtered_mcp_tools)

    # 5. Convert definitions to the target vendor format
    target_vendor = vendor or "openai" # Default to OpenAI if vendor is None

    if target_vendor == "gemini":
        # For Gemini, convert to FunctionDeclaration objects and return as Tool
        function_declarations = [convert_tool_definition_for_vendor(tool_def, "gemini") for tool_def in canonical_defs]
        return types.Tool(function_declarations=function_declarations)
    else:
        # For other vendors, convert to their specific format
        # Ensure all definitions are dictionaries for list return type
        vendor_defs = [convert_tool_definition_for_vendor(tool_def, target_vendor) for tool_def in canonical_defs]
        # Ensure all items are dicts (Gemini returns types.FunctionDeclaration)
        return [d for d in vendor_defs if isinstance(d, dict)]

def get_gemini_tool_definitions(without_human_fallback: bool = False, mcp_tools: Optional[List[CanonicalToolDefinition]] = None) -> types.Tool:
    """
    Get all function definitions for Gemini API function calling.

    Args:
        without_human_fallback: Whether to exclude the need_ask_human tool
        mcp_tools: Optional list of canonical tool definitions from MCP servers

    Returns:
        types.Tool: A list of tool definitions in Gemini API format
    """
    return get_tool_definitions(without_human_fallback, vendor="gemini", mcp_tools=mcp_tools)

def get_anthropic_tool_definitions(without_human_fallback: bool = False, mcp_tools: Optional[List[CanonicalToolDefinition]] = None) -> List[Dict[str, Any]]:
    """
    Get all function definitions for Anthropic Claude API function calling.

    Args:
        without_human_fallback: Whether to exclude the need_ask_human tool
        mcp_tools: Optional list of canonical tool definitions from MCP servers

    Returns:
        List[Dict[str, Any]]: A list of tool definitions in Anthropic Claude API format
    """
    return get_tool_definitions(without_human_fallback, vendor="anthropic", mcp_tools=mcp_tools) 