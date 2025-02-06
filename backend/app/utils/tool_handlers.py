from typing import Any, Dict, List, AsyncGenerator, Union
import json
from app.utils.search_utils import web_search
from app.utils.extract_web_utils import web_browsing
from app.utils.logging_utils import get_logger, log_error, log_info, log_warning, log_debug

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
    return "\n".join(formatted_text)

async def handle_tool_call(
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
            "tool_calls": [tool_call.model_dump()]
        })

        if tool_call.function.name == "web_search":
            query = args.get("query")
            num_results = args.get("num_results", 5)
            
            if query:
                log_info("Executing web search", {"query": query, "num_results": num_results})
                yield f"data: {json.dumps({'type': 'tool_execution', 'tool': 'web_search', 'query': query})}\n\n"
                
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
                yield f"data: {json.dumps({'type': 'tool_execution', 'tool': 'web_browsing', 'url': url})}\n\n"
                
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

def parse_usage(usage: Any) -> Dict[str, Any]:
    """
    Parse usage information from OpenAI's response.
    This is a common utility used by both streaming and non-streaming responses.

    Args:
        usage: The usage object from OpenAI's response

    Returns:
        Dict containing parsed usage information
    """
    completion_usage = getattr(usage, 'completion_tokens', 0)
    prompt_usage = getattr(usage, 'prompt_tokens', 0)
    
    completion_tokens_details = getattr(usage, 'completion_tokens_details', None)
    reasoning_usage = getattr(completion_tokens_details, 'reasoning_tokens', 0) if completion_tokens_details else 0

    usage_info = {
        "completion_usage": completion_usage,
        "prompt_usage": prompt_usage,
        "reasoning_usage": reasoning_usage
    }
    
    log_info("Token usage", usage_info)
    return usage_info 