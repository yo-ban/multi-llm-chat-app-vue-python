from typing import Any, Dict, List, AsyncGenerator, Union
import json
from app.function_calling.web_search_tool import web_search
from app.function_calling.web_browsing_tool import web_browsing
from app.function_calling.need_ask_human_tool import need_ask_human
from app.logger.logging_utils import get_logger, log_error, log_info, log_warning, log_debug

# Get logger instance
logger = get_logger()

def format_search_results(results: List[Any]) -> str:
    """Format web search results into a readable text format."""
    formatted_text = []
    for i, result in enumerate(results, 1):
        formatted_text.append(f"{i}. {result.title}")
        formatted_text.append(f"   {result.link}")
        if result.snippet:
            formatted_text.append(f"   {result.snippet}\n")
    return "\n".join(formatted_text)

def format_web_extraction(result: Dict[str, Any]) -> str:
    """Format web extraction results into a readable text format."""
    if result.get("status") == "error":
        return f"Error extracting content: {result.get('error', 'Unknown error')}"
    
    formatted_text = []
    formatted_text.append(f"Extracted from: {result['url']}")
    if result.get("extracted_info"):
        formatted_text.append(f"\n{result['extracted_info']}")
    if result.get("error"):
        formatted_text.append(f"\n{result['error']}")
    return "\n".join(formatted_text)

async def openai_handle_tool_call(
    tool_call: Any,
    messages: List[Dict[str, Any]]
) -> AsyncGenerator[str, None]:
    """
    Handle a tool call and update the message history with results.
    This is a common handler used by both streaming and non-streaming responses.

    Args:
        tool_call: The tool call object from OpenAI's response
        messages: The current message history to update with results

    Yields:
        SSE formatted strings containing tool execution status and results
    """
    try:
        args = json.loads(tool_call.function.arguments)
        # Add the tool call to message history
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tool_call.id.replace("\\", ""),
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }
            ]
        })

        if tool_call.function.name == "web_search":
            query = args.get("query")
            num_results = args.get("num_results", 5)
            
            if query:
                log_info("Executing web search", {"query": query, "num_results": num_results})
                yield {'type': 'tool_execution', 'tool': 'web_search', 'query': query}
                
                results = await web_search(query, num_results)

                formatted_results = format_search_results(results)
                
                # Add formatted results to message history for the model
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": formatted_results  # Use formatted text instead of JSON
                })
                
        elif tool_call.function.name == "web_browsing":
            url = args.get("url")
            query = args.get("query")
            
            if url and query:
                log_info("Executing web extraction", {"url": url, "query": query})
                yield {'type': 'tool_execution', 'tool': 'web_browsing', 'url': url}
                
                result = await web_browsing(url, query)

                formatted_result = format_web_extraction(result)
                
                # Add formatted result to message history for the model
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": formatted_result  # Use formatted text instead of JSON
                })
            else:
                log_warning("No URL or query provided for web browsing")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": "Invalid arguments provided for web browsing. Try to check tool definitions and validate the arguments again."
                })

        elif tool_call.function.name == "need_ask_human":
            clarification_points = args.get("clarification_points")

            if clarification_points:
                log_info("Executing need_ask_human", {"clarification_points": clarification_points})

                result = await need_ask_human(clarification_points)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": result
                })

        else:
            log_warning(f"Unknown tool called: {tool_call.function.name}")
            
    except json.JSONDecodeError as e:
        log_error(f"Failed to parse tool arguments: {str(e)}", {
            "tool": tool_call.function.name,
            "arguments": tool_call.function.arguments
        })
        raise
        
    except Exception as e:
        log_error(f"Error handling tool call: {str(e)}", {
            "tool": tool_call.function.name,
            "error": str(e)
        })
        raise


async def gemini_handle_tool_call(
    function_call: Any
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Handle a tool call from Gemini API and execute the requested tool.
    This is a common handler used by both streaming and non-streaming responses.

    Args:
        function_call: The function call object from Gemini's response
        history: The current message history (for context if needed)

    Yields:
        Tool execution status updates for frontend
    Returns:
        The tool execution results will be returned via the last yielded status update
    """
    result = None
    try:
        args = function_call.args
        
        if function_call.name == "web_search":
            query = args.get("query")
            num_results = args.get("num_results", 5)
            
            if query:
                log_info("Executing web search", {"query": query, "num_results": num_results})
                yield {"type": "tool_execution", "tool": "web_search", "query": query}
                
                results = await web_search(query, num_results)
                result = format_search_results(results)
                
        elif function_call.name == "web_browsing":
            url = args.get("url")
            query = args.get("query")
            
            if url and query:
                log_info("Executing web extraction", {"url": url, "query": query})
                yield {"type": "tool_execution", "tool": "web_browsing", "url": url}
                
                browse_result = await web_browsing(url, query)
                result = format_web_extraction(browse_result)
        
        elif function_call.name == "need_ask_human":
            clarification_points = args.get("clarification_points")

            if clarification_points:
                log_info("Executing need_ask_human", {"clarification_points": clarification_points})
                result = await need_ask_human(clarification_points)

        else:
            log_warning(f"Unknown tool called: {function_call.name}")
            
        # Return the final result in the last status update
        if result:
            yield {"type": "tool_execution_complete", "tool": function_call.name, "result": result}
            
    except Exception as e:
        log_error(f"Error handling tool call: {str(e)}", {
            "tool": function_call.name,
            "error": str(e)
        })
        raise
