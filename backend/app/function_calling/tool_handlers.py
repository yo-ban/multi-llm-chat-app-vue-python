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

async def handle_tool_call(
    tool_name: str,
    tool_input: Dict[str, Any]
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Handle a tool call from any LLM API and execute the requested tool.
    
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
        if tool_name == "web_search":
            query = tool_input.get("query")
            num_results = tool_input.get("num_results", 5)
            
            if query:
                log_info("Executing web search", {"query": query, "num_results": num_results})
                yield {"type": "tool_execution", "tool": "web_search", "query": query}
                
                results = await web_search(query, num_results)
                result = format_search_results(results)
                
        elif tool_name == "web_browsing":
            url = tool_input.get("url")
            query = tool_input.get("query")
            
            if url and query:
                log_info("Executing web extraction", {"url": url, "query": query})
                yield {"type": "tool_execution", "tool": "web_browsing", "url": url}
                
                browse_result = await web_browsing(url, query)
                result = format_web_extraction(browse_result)
            else:
                log_warning("No URL or query provided for web browsing")
                yield {"type": "error", "message": "Invalid arguments provided for web browsing"}
        
        elif tool_name == "need_ask_human":
            clarification_points = tool_input.get("clarification_points")

            if clarification_points:
                log_info("Executing need_ask_human", {"clarification_points": clarification_points})
                result = await need_ask_human(clarification_points)

        else:
            log_warning(f"Unknown tool called: {tool_name}")
            
        # Return the final result in the last status update
        if result:
            log_info("Tool execution complete", {"tool": tool_name, "result": result})
            yield {"type": "tool_execution_complete", "tool": tool_name, "result": result}
            
    except Exception as e:
        log_error(f"Error handling tool call: {str(e)}", {
            "tool": tool_name,
            "error": str(e)
        })
        raise

# For backward compatibility, keep aliases to the unified function
openai_handle_tool_call = handle_tool_call
gemini_handle_tool_call = handle_tool_call
anthropic_handle_tool_call = handle_tool_call
