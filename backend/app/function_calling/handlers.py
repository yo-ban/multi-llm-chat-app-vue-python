from typing import Any, Dict, List, AsyncGenerator, Union
import json
import inspect
from sqlalchemy.orm import Session # DBアクセス用
from app.infrastructure.database import SessionLocal # DBセッション取得用
from app.application.settings.service import SettingsService # 設定サービス用

# Remove explicit tool imports
from app.logger.logging_utils import get_logger, log_error, log_info, log_warning, log_debug
# Import the dynamic tool discovery function
from app.function_calling.definitions import get_available_tools

from poly_mcp_client import PolyMCPClient

# Get logger instance
logger = get_logger()

# Build the tool function map dynamically
# Note: @lru_cache on get_available_tools ensures this scan happens only once (per cache settings)
tool_functions_map = {func.__name__: func for func in get_available_tools()}

async def handle_tool_call(
    tool_name: str,
    tool_input: Dict[str, Any],
    mcp_manager: PolyMCPClient
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Handle a tool call by executing either a local function or an MCP server tool.

    Args:
        tool_name: The name of the tool to execute (e.g., "web_search" or "server_name/readFile")
        tool_input: The input parameters for the tool
        mcp_manager: The PolyMCPClient instance for executing external tools

    Yields:
        Tool execution status updates for frontend
    Returns:
        The tool execution results will be returned via the last yielded status update
    """
    result = None
    result_to_return = []
    is_mcp_tool = "mcp-" in tool_name # MCPツールかどうかの判定

    try:
        if is_mcp_tool:
            # --- MCP Tool Execution ---
            log_info(f"Executing MCP tool: {tool_name}", {"input": tool_input})
            # フロントエンドへの開始通知
            yield {"type": "tool_execution", "tool": tool_name, "input": tool_input}

            try:
                # PolyMCPClient を使ってツールを実行
                results = await mcp_manager.execute_mcp_tool(tool_name, tool_input)

                # Anthropic format
                for result in results:
                    if result.type == "text":
                        result_to_return.append(
                            {
                                "type": "text", 
                                "text": result.text
                            }
                        )
                    elif result.type == "image":
                        # Add the image source to the result
                        result_to_return.append(
                            {
                                "type": "image", 
                                "source": {
                                    "type": "base64",
                                    "media_type": result.mimeType, 
                                    "data": result.data
                                }
                            }
                        )
                    # elif result.type == "embedded_resource":
                    #     result_to_return.append({"type": "embedded_resource", "resource": result.resource})

            except Exception as e:
                log_error(f"Error executing MCP tool: {str(e)}", {"tool": tool_name, "input": tool_input})
                yield {"type": "error", "message": f"Error executing MCP tool {tool_name}: {str(e)}"}
                result_to_return.append({"type": "text", "text": f"Error executing MCP tool {tool_name}: {str(e)}"})
                # エラーが発生しても Generator は終了させない（呼び出し元で制御）

        else:
            # --- Local Tool Execution ---
            tool_func = tool_functions_map.get(tool_name)

            if tool_func:
                log_info(f"Executing tool: {tool_name}", {"input": tool_input})
                # Simplified yield for demonstration
                yield {"type": "tool_execution", "tool": tool_name, "input": tool_input}

                # Sanitize tool_input to only include valid parameters for the tool function
                valid_params = {}
                sig = inspect.signature(tool_func)
                param_names = set(sig.parameters.keys())
                
                for key, value in tool_input.items():
                    if key in param_names:
                        valid_params[key] = value
                    else:
                        log_warning(f"Ignoring invalid parameter '{key}' for tool '{tool_name}'")
                
                try:
                    # ローカルツール実行 (既存ロジック)
                    result = await tool_func(**valid_params)
                    log_info(f"Local tool execution complete: {tool_name}")

                    result_to_return.append({"type": "text", "text": result})

                    # Return the final result in the last status update
                    if result_to_return: # Check for None explicitly, as some tools might return False/0
                        yield {"type": "tool_execution_complete", "tool": tool_name, "result": json.dumps(result_to_return)}
                    else:
                        log_warning(f"Local Tool execution completed, but no result was returned: {tool_name}")
                        yield {"type": "tool_execution_complete", "tool": tool_name, "result": "Tool execution completed, but no result was returned."}

                except Exception as e:
                    log_error(f"Error executing local tool: {str(e)}", {"tool": tool_name, "input": tool_input})
                    yield {"type": "error", "message": f"Error executing local tool {tool_name}: {str(e)}"}
                    # エラーが発生しても Generator は終了させない

            else:
                log_warning(f"Unknown local tool called: {tool_name}")
                yield {"type": "error", "message": f"Unknown local tool: {tool_name}"}


        if not result_to_return:
            log_warning(f"Tool execution completed, but no result was returned: {tool_name}")
            result_to_return.append({"type": "text", "text": f"{tool_name} execution completed, but no result was returned."})

        yield {"type": "tool_execution_complete", "tool": tool_name, "result": json.dumps(result_to_return)}


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
