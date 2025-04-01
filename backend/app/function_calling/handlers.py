from typing import Any, Dict, List, AsyncGenerator, Union
import json
# Remove explicit tool imports
from app.logger.logging_utils import get_logger, log_error, log_info, log_warning, log_debug
# Import the dynamic tool discovery function
from app.function_calling.definitions import get_available_tools

# Get logger instance
logger = get_logger()

# Build the tool function map dynamically
# Note: @lru_cache on get_available_tools ensures this scan happens only once (per cache settings)
tool_functions_map = {func.__name__: func for func in get_available_tools()}

async def handle_tool_call(
    tool_name: str,
    tool_input: Dict[str, Any]
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Handle a tool call from any LLM API by dynamically finding and executing the requested tool.

    Args:
        tool_name: The name of the tool to execute
        tool_input: The input parameters for the tool

    Yields:
        Tool execution status updates for frontend
    Returns:
        The tool execution results will be returned via the last yielded status update
    """
    result = None
    try:
        # Find the tool function from the dynamically built map
        tool_func = tool_functions_map.get(tool_name)

        if tool_func:
            log_info(f"Executing tool: {tool_name}", {"input": tool_input})
            # Assuming yield format is consistent or handled within the tool itself if needed
            # Simplified yield for demonstration. You might need a more generic yield here.
            yield {"type": "tool_execution", "tool": tool_name, "input": tool_input}

            # Execute the tool dynamically, passing arguments using **
            # Ensure the tool function is async
            result = await tool_func(**tool_input)

        else:
            log_warning(f"Unknown tool called: {tool_name}")
            yield {"type": "error", "message": f"Unknown tool: {tool_name}"}

        # Return the final result in the last status update
        if result is not None: # Check for None explicitly, as some tools might return False/0
            log_info("Tool execution complete", {"tool": tool_name, "result": result})
            yield {"type": "tool_execution_complete", "tool": tool_name, "result": result}

    except Exception as e:
        log_error(f"Error handling tool call: {str(e)}", {
            "tool": tool_name,
            "error": str(e)
        })
        # Consider yielding an error message to the frontend as well
        yield {"type": "error", "message": f"Error executing tool {tool_name}: {str(e)}"}
        # Depending on desired behavior, you might not want to re-raise here
        # or handle specific exceptions differently.
        raise

# Remove the old, unused tool_functions dictionary and aliases if they are no longer needed elsewhere
# openai_handle_tool_call = handle_tool_call
# gemini_handle_tool_call = handle_tool_call
# anthropic_handle_tool_call = handle_tool_call 