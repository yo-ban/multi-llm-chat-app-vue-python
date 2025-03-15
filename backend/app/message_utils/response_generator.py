import json
import base64
from typing import AsyncGenerator, Any, Dict, List
from openai import AsyncOpenAI
from app.function_calling.tool_handlers import openai_handle_tool_call, gemini_handle_tool_call
from app.function_calling.tool_definitions import get_tool_definitions, get_gemini_tool_definitions
from app.message_utils.usage_parser import parse_usage, parse_usage_gemini, parse_usage_anthropic
from app.logger.logging_utils import get_logger, log_error, log_info, log_warning, log_debug
from google.genai.client import Client
from google.genai.types import (
    GenerateContentConfig,
    Content,
    Part,
    ToolConfig,
    FunctionCallingConfig
)

# Get logger instance
logger = get_logger()

async def gemini_stream_generator(
    response: Any,
    gemini_client: Client,
    model: str,
    history: list[Content],
    completion_args: dict,
    images: list
) -> AsyncGenerator[str, None]:
    """
    Generate streaming response for Gemini API.
    Handles both regular text responses and function calls.
    
    Args:
        response: Initial Gemini API streaming response
        gemini_client: Gemini client instance
        model: The full model string (e.g., "gemini-2.5-flash").
        history: Current conversation history
        completion_args: Generation configuration including tools and settings
        images: List of uploaded images
        
    Yields:
        Streaming response data in SSE format
    """

    # Insert helper function to process inline image data
    async def _yield_inline_image(inline_data) -> AsyncGenerator[str, None]:
        try:
            mime_type = inline_data.mime_type
            data = inline_data.data
            # Check the type of data and encode if necessary
            if isinstance(data, bytes):
                base64_data = base64.b64encode(data).decode('utf-8')
            elif isinstance(data, str):
                # Assume data is already a proper base64 encoded string
                base64_data = data
            else:
                log_error(f"Unexpected type for inline_data.data: {type(data)}")
                base64_data = str(data)

            yield f"data: {json.dumps({'type': 'image_start', 'mime_type': mime_type})}\n\n"
            chunk_size = 8192  # 8KB chunks
            for i in range(0, len(base64_data), chunk_size):
                chunk = base64_data[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'image_chunk', 'chunk': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'image_end'})}\n\n"
        except Exception as e:
            log_error(f"Error processing image data: {str(e)}")

    # Cleanup uploaded images
    def _cleanup_images():
        for image in images:
            try:
                gemini_client.files.delete(name=image.name)
            except Exception as e:
                print(f"Error deleting image: {e}")

    try:
        latest_usage = None
        should_continue = True
        tool_calls_count = 0
        
        while should_continue:  # Loop to handle recursive tool calls
            text = ""
            has_function_call = False

            async for event in response:
                # Handle function calls if present
                if event.candidates[0].content:
                    if event.candidates[0].content.parts:
                        part = event.candidates[0].content.parts[0]

                        if part.function_call:
                            has_function_call = True

                            # Initialize parts lists
                            function_call_parts = []
                            function_response_parts = []
                            text_parts = []

                            # Add text parts if present
                            if text:
                                text_parts.append(Part.from_text(text=text))

                            # Handle function calls
                            for function_call in event.function_calls:
                                # Notify about tool call start
                                yield f"data: {json.dumps({'type': 'tool_call_start', 'tool': function_call.name})}\n\n"
                                
                                # Handle the tool call
                                tool_result = None
                                async for status in gemini_handle_tool_call(function_call):
                                    if status["type"] == "tool_execution_complete":
                                        tool_result = status["result"]
                                    else:
                                        # Forward status updates to frontend
                                        yield f"data: {json.dumps(status)}\n\n"
                                
                                # Create function call part with the tool result
                                function_call_part = Part.from_function_call(
                                    name=function_call.name,
                                    args=function_call.args
                                )
                                function_call_parts.append(function_call_part)

                                # Create function response part with the tool result
                                function_response_part = Part.from_function_response(
                                    name=function_call.name,
                                    response={"output": tool_result}
                                )
                                function_response_parts.append(function_response_part)
                            
                                yield f"data: {json.dumps({'type': 'tool_call_end', 'tool': function_call.name})}\n\n"

                            # Create function call content
                            function_call_content = Content(
                                role="model",
                                parts=text_parts + function_call_parts
                            )

                            # Create function response content
                            function_response_content = Content(
                                role="user",
                                parts=function_response_parts
                            )

                            # Update history with function call and response
                            history = history + [function_call_content, function_response_content]

                            # Change tool config to AUTO
                            tool_config = ToolConfig(
                                function_calling_config=FunctionCallingConfig(mode='AUTO')
                            )
                            completion_args["tool_config"] = tool_config

                            if tool_calls_count > 0:
                                completion_args["tools"] = [get_gemini_tool_definitions()]

                            tool_calls_count += 1

                            # Get new response incorporating tool results
                            response = await gemini_client.aio.models.generate_content_stream(
                                model=model,
                                contents=history,
                                config=GenerateContentConfig(**completion_args)
                            )
                            
                            break  # Break inner loop to start new response processing
                        
                        if part.inline_data:
                            async for inline_chunk in _yield_inline_image(part.inline_data):
                                yield inline_chunk

                        # Handle regular text content
                        if part.text:
                            text += event.text
                            yield f"data: {json.dumps({'text': event.text})}\n\n"

                        if event.candidates:
                            if event.candidates[0].finish_reason:
                                if event.usage_metadata:
                                    latest_usage = event.usage_metadata

            # If no function calls were made, we're done
            if not has_function_call:
                should_continue = False
                # Handle usage metadata if present
                usage = await parse_usage_gemini(latest_usage)
                log_info("Token usage in Gemini", usage)
                yield f"data: {json.dumps(usage)}\n\n"
                yield f"data: {json.dumps({'text': '[DONE]'})}\n\n"
                _cleanup_images()
                break

    except Exception as e:
        log_error(f"Error in Gemini stream generator: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

async def gemini_non_stream_generator(
    response: Any,
    gemini_client: Client,
    model: str,
    history: list[Content],
    completion_args: dict,
    images: list
) -> AsyncGenerator[str, None]:
    """
    Generate non-streaming response for Gemini API.
    Handles both regular text responses and function calls.
    
    Args:
        response: Initial Gemini API non-streaming response
        gemini_client: Gemini client instance
        model: The full model string (e.g., "gemini-2.5-flash").
        history: Current conversation history
        completion_args: Generation configuration including tools and settings
        
    Yields:
        Response data in SSE format
    """
    try:
        # Handle function calls if present
        if hasattr(response, 'function_calls'):
            for function_call in response.function_calls:
                # Notify about tool call start
                yield f"data: {json.dumps({'type': 'tool_call_start', 'tool': function_call.name})}\n\n"
                
                # Handle the tool call
                tool_result = None
                async for status in gemini_handle_tool_call(function_call):
                    if status["type"] == "tool_execution_complete":
                        tool_result = status["result"]
                    else:
                        # Forward status updates to frontend
                        yield f"data: {json.dumps(status)}\n\n"
                
                # Create function response content with the tool result
                function_response_part = Part.from_function_response(
                    name=function_call.name,
                    response={"result": tool_result}
                )
                function_response_content = Content(
                    role="tool",
                    parts=[function_response_part]
                )
                
                # Change tool config to AUTO
                tool_config = ToolConfig(
                    function_calling_config=FunctionCallingConfig(mode='AUTO')
                )
                completion_args["tool_config"] = tool_config

                # Create new chat with updated history
                chat = gemini_client.aio.chats.create(
                    history=history,
                    model=model,
                    config=GenerateContentConfig(**completion_args)
                )
                
                # Get final response incorporating tool results
                response = await chat.send_message(function_response_content)

        # Output the final text response
        if hasattr(response, 'text'):
            yield f'data: {json.dumps({"text": response.text})}\n\n'

        # Handle usage metadata if present
        if response.usage_metadata:
            usage = await parse_usage_gemini(response.usage_metadata)
            log_info("Token usage in Gemini", usage)
            yield f"data: {json.dumps(usage)}\n\n"

        yield 'data: {"text": "[DONE]"}\n\n'

    except Exception as e:
        log_error(f"Error in Gemini non-stream generator: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


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
        tool_calls_count = 0
        text_generated = False
        
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
                                async for status in openai_handle_tool_call(complete_call, openai_messages):
                                    yield f"data: {json.dumps(status)}\n\n"
                                
                                # Update messages for the next API call
                                completion_args['messages'] = openai_messages
                                completion_args['tools'] = get_tool_definitions()
                                if tool_calls_count > 0:
                                    completion_args['tool_choice'] = "auto"
                                
                                tool_calls_count += 1
                                tool_calls_buffer = {}  # Reset buffer for next iteration

                                yield f"data: {json.dumps({'type': 'tool_call_end', 'tool': tool_call.function.name})}\n\n"
                                break  # Break inner loop to start new API call
                    
                    # Handle regular text content
                    elif hasattr(delta, 'content') and delta.content is not None:
                        yield f"data: {json.dumps({'text': delta.content})}\n\n"
                        text_generated = True

                # Check finish reason
                if chunk.choices and chunk.choices[0].finish_reason:
                    
                    if chunk.usage:
                        usage = await parse_usage(chunk.usage)
                        log_info("Token usage in OpenAI", usage)
                        yield f"data: {json.dumps(usage)}\n\n"

                    if chunk.choices[0].finish_reason == 'stop' and text_generated:
                        log_info("Stream generator ended normally")
                        should_continue = False
                        break
                    elif chunk.choices[0].finish_reason == 'stop' and not text_generated:
                        log_info("Stream generator ended but no text generated")
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
        async for status in openai_handle_tool_call(tool_call, openai_messages):
            yield f"data: {json.dumps(status)}\n\n"
        
        completion_args['messages'] = openai_messages
        completion_args['tool_choice'] = "auto"
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
        usage = {}
        async for event in response:
            if event.type == "content_block_start":
                if event.content_block.type == "thinking":
                    print(f"思考：{event.content_block.thinking}", end="", flush=True)
                elif event.content_block.type == "text":
                    yield f"data: {json.dumps({'text': event.content_block.text})}\n\n"
            elif event.type == "content_block_delta":
                if event.delta.type == "thinking_delta":
                    print(f"{event.delta.thinking}", end="", flush=True)
                elif event.delta.type == "text_delta":
                    yield f"data: {json.dumps({'text': event.delta.text})}\n\n"
            elif event.type == "content_block_stop":
                pass
            elif event.type == "message_start":
                message = event.message
                if hasattr(message, 'usage'):
                    usage_start = await parse_usage_anthropic(message.usage)
                    log_info("Token usage in Anthropic in message_start", usage_start)
                    usage.update(usage_start)
            elif event.type == "message_delta":
                if hasattr(event, 'usage'):
                    usage_delta = await parse_usage_anthropic(event.usage)
                    log_info("Token usage in Anthropic in message_delta", usage_delta)
                    usage.update(usage_delta)
                    yield f"data: {json.dumps(usage)}\n\n"
                yield f"data: {json.dumps({'stop_reason': event.delta.stop_reason})}\n\n"
            elif event.type == "message_stop":
                yield f"data: {json.dumps({'text': '[DONE]'})}\n\n"
            elif event.type == "ping":
                yield ": ping\n\n"
            elif event.type == "error":
                raise Exception(event.error.message)
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n" 