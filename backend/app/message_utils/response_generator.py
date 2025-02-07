import json
from typing import AsyncGenerator, Any, Dict, List
from openai import AsyncOpenAI
from app.function_calling.tool_handlers import handle_tool_call
from app.message_utils.usage_parser import parse_usage, parse_usage_gemini
from app.logger.logging_utils import get_logger, log_error, log_info, log_warning, log_debug

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

async def gemini_non_stream_generator(response) -> AsyncGenerator[str, None]:
    yield f'data: {json.dumps({"text": response.text})}\n\n'

    if response.usage_metadata:
        usage = await parse_usage_gemini(response.usage_metadata)
        log_info("Token usage in Gemini", usage)
        yield f"data: {json.dumps(usage)}\n\n"

    yield 'data: {"text": "[DONE]"}\n\n'


async def openai_stream_generator(
    response: Any,
    openai_client: AsyncOpenAI,
    openai_messages: List[Dict[str, Any]],
    completion_args: dict
) -> AsyncGenerator[str, None]:
    """
    Generator for streaming OpenAI API responses.
    This function also handles tool_calls if present in the response.
    
    Args:
        response: Initial OpenAI API response
        openai_client: OpenAI client instance
        openai_messages: Current message history
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
                                async for status in handle_tool_call(complete_call, openai_messages):
                                    yield status
                                
                                # Update messages for the next API call
                                completion_args['messages'] = openai_messages
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


async def openai_non_stream_generator(
    openai_client: AsyncOpenAI,
    completion_args: dict,
    openai_messages: list
) -> AsyncGenerator[str, None]:
    """
    Common processing for non-streaming OpenAI API calls.
    This function also handles tool_calls if present in the response.
    Returns the response as a streaming response for consistency with streaming mode.
    
    Args:
        openai_client: The AsyncOpenAI client instance.
        completion_args: The arguments to pass to the API call.
        model: The full model string (e.g., "openai-gpt4").
        openai_messages: Formatted conversation messages.
    
    Returns:
        A StreamingResponse containing the response message.
    """
    response = await openai_client.chat.completions.create(**completion_args)

    # Check if a tool_call is present in the response
    while response.choices[0].message.tool_calls:
        tool_call = response.choices[0].message.tool_calls[0]

        yield f"data: {json.dumps({'type': 'tool_call_start', 'tool': tool_call.function.name})}\n\n"

        # Handle the tool call using common handler and yield status updates
        async for status in handle_tool_call(tool_call, openai_messages):
            yield status
        
        completion_args['messages'] = openai_messages

        # Get final response incorporating tool results with tools enabled
        final_response = await openai_client.chat.completions.create(
            **completion_args,
        )
        response = final_response  # Update response for next iteration check
    
    # After all tool calls are processed, return the final content
    if response.choices[0].message.content:
        yield f'data: {json.dumps({"text": response.choices[0].message.content})}\n\n'

    if response.usage:
        usage = await parse_usage(response.usage)
        log_info("Token usage in OpenAI", usage)
        yield f"data: {json.dumps(usage)}\n\n"
    
    yield 'data: {"text": "[DONE]"}\n\n'


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