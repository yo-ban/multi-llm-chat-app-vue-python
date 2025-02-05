import json
from typing import AsyncGenerator, Any, Dict, List
from openai import AsyncOpenAI
from app.utils.tool_handlers import handle_tool_call, parse_usage
from app.utils.logging_utils import get_logger, log_error, log_info, log_warning, log_debug

# Get logger instance
logger = get_logger()

async def gemini_stream_generator(response) -> AsyncGenerator[str, None]:
    """
    Generate streaming response for Gemini API
    """
    try:
        async for event in response:
            yield f"data: {json.dumps({'text': event.text})}\n\n"
        yield f"data: {json.dumps({'text': '[DONE]'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

async def openai_stream_generator(
    response: Any,
    openai_client: AsyncOpenAI = None,
    messages: List[Dict[str, Any]] = None,
    model: str = None
) -> AsyncGenerator[str, None]:
    """
    Generate streaming response for OpenAI API with function calling support
    
    Args:
        response: Initial OpenAI API response
        openai_client: OpenAI client instance (needed for function calling)
        messages: Current message history (needed for function calling)
        model: Model name without prefix (needed for function calling)
    """
    try:
        tool_calls_buffer = {}
        
        async for chunk in response:
            if chunk.choices:
                delta = chunk.choices[0].delta

                # Handle tool calls
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        index = tool_call.index
                        
                        if index not in tool_calls_buffer:
                            tool_calls_buffer[index] = tool_call
                            # First chunk of a tool call
                            yield f"data: {json.dumps({'type': 'tool_call_start', 'tool': tool_call.function.name})}\n\n"
                        else:
                            # Accumulate arguments
                            tool_calls_buffer[index].function.arguments += tool_call.function.arguments or ""
                            
                        # If we have complete arguments, execute the function
                        if tool_call.function.arguments and tool_call.function.arguments.endswith("}"):
                            complete_call = tool_calls_buffer[index]
                            
                            if openai_client and messages and model:
                                # Handle the tool call using common handler
                                async for status in handle_tool_call(complete_call, messages):
                                    yield status
                                
                                # Get final response incorporating tool results
                                final_response = await openai_client.chat.completions.create(
                                    model=model,
                                    messages=messages,
                                    stream=True,
                                    stream_options={"include_usage": True}
                                )
                                
                                async for final_chunk in final_response:
                                    if final_chunk.choices:
                                        if final_chunk.choices[0].delta.content:
                                            yield f"data: {json.dumps({'text': final_chunk.choices[0].delta.content})}\n\n"
                                    if final_chunk.usage:
                                        usage = parse_usage(final_chunk.usage)
                                        yield f"data: {json.dumps(usage)}\n\n"
                
                # Handle regular text content
                elif delta.content:
                    yield f"data: {json.dumps({'text': delta.content})}\n\n"

            if chunk.usage:
                usage = parse_usage(chunk.usage)
                yield f"data: {json.dumps(usage)}\n\n"

        yield f"data: {json.dumps({'text': '[DONE]'})}\n\n"
        
    except Exception as e:
        log_error(f"Error in stream generator: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

async def anthropic_stream_generator(response) -> AsyncGenerator[str, None]:
    """
    Generate streaming response for Anthropic API
    """
    try:
        async for event in response:
            if event.type == "content_block_start":
                yield f"data: {json.dumps({'text': event.content_block.text})}\n\n"
            elif event.type == "content_block_delta":
                yield f"data: {json.dumps({'text': event.delta.text})}\n\n"
            elif event.type == "content_block_stop":
                pass
            elif event.type == "message_delta":
                yield f"data: {json.dumps({'stop_reason': event.delta.stop_reason})}\n\n"
            elif event.type == "message_stop":
                yield f"data: {json.dumps({'text': '[DONE]'})}\n\n"
            elif event.type == "ping":
                yield ": ping\n\n"
            elif event.type == "error":
                raise Exception(event.error.message)
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n" 