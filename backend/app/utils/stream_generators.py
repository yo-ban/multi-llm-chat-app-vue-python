import json
from typing import AsyncGenerator, Any, Dict, List
from openai import AsyncOpenAI
from app.function_calling.tool_handlers import handle_tool_call
from app.utils.message_utils import parse_usage, parse_usage_gemini
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

        if event.usage_metadata:
            usage = await parse_usage_gemini(event.usage_metadata)
            log_info("Token usage in Gemini", usage)
            yield f"data: {json.dumps(usage)}\n\n"

        yield f"data: {json.dumps({'text': '[DONE]'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

async def openai_stream_generator(
    response: Any,
    openai_client: AsyncOpenAI,
    messages: List[Dict[str, Any]],
    completion_args: dict
) -> AsyncGenerator[str, None]:
    """
    Generator for streaming OpenAI API responses.
    This function also handles tool_calls if present in the response.
    
    Args:
        response: Initial OpenAI API response
        openai_client: OpenAI client instance
        messages: Current message history
        completion_args: The arguments to pass to the API call
    
    Yields:
        Streaming response data.
    """
    try:
        tool_calls_buffer = {}
        should_continue = True
        
        while should_continue:  # Loop to handle recursive tool calls
            stream = response if response else await openai_client.chat.completions.create(
                **completion_args
            )
            response = None  # Reset response after first use
            log_info("Stream generator started")
            has_tool_call = False

            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta

                    # Handle tool calls
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        has_tool_call = True
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
                                
                                # Handle the tool call using common handler
                                async for status in handle_tool_call(complete_call, messages):
                                    yield status
                                
                                # Update messages for the next API call
                                completion_args['messages'] = messages
                                tool_calls_buffer = {}  # Reset buffer for next iteration
                                break  # Break inner loop to start new API call
                    
                    # Handle regular text content
                    elif hasattr(delta, 'content') and delta.content is not None:
                        yield f"data: {json.dumps({'text': delta.content})}\n\n"

                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = await parse_usage(chunk.usage)
                    log_info("Token usage in OpenAI", usage)
                    yield f"data: {json.dumps(usage)}\n\n"

                # Check finish reason
                if chunk.choices and chunk.choices[0].finish_reason:
                    if chunk.choices[0].finish_reason == 'stop':
                        log_info("Stream generator ended normally")
                        should_continue = False
                        break
                    elif chunk.choices[0].finish_reason == 'tool_calls':
                        log_info("Tool call completed, continuing with new request")
                        break

            # Determine whether to continue based on the last chunk
            if not has_tool_call or not should_continue:
                yield 'data: {"text": "[DONE]"}\n\n'
                break

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