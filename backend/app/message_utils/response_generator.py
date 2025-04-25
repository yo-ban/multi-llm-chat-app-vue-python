import json
import base64
from typing import AsyncGenerator, Any, Dict, List
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.function_calling.handlers import handle_tool_call
from app.function_calling.definitions import get_tool_definitions, get_gemini_tool_definitions, get_anthropic_tool_definitions
from app.message_utils.usage_parser import parse_usage, parse_usage_gemini, parse_usage_anthropic
from app.logger.logging_utils import get_logger, log_error, log_info, log_warning, log_debug
from app.misc_utils.image_utils import upload_image_to_gemini

from google.genai.client import Client
from google.genai.types import (
    GenerateContentConfig,
    Content,
    Part,
    ToolConfig,
    FunctionCallingConfig,
    GenerateContentResponsePromptFeedback
)

from poly_mcp_client import PolyMCPClient
from poly_mcp_client.models import CanonicalToolDefinition
# Get logger instance
logger = get_logger()

async def gemini_stream_generator(
    response: Any,
    gemini_client: Client,
    model: str,
    history: list[Content],
    completion_args: dict,
    images: list,
    mcp_manager: PolyMCPClient,
    enabled_tools: list[CanonicalToolDefinition],
    multimodal: bool = False
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
        # Create a running copy of completion args to maintain context
        running_args = completion_args.copy()
        # Keep track of the conversation history
        running_history = history.copy()
        
        while should_continue:  # Loop to handle recursive tool calls
            text = ""
            has_function_call = False

            async for event in response:
                # Handle function calls if present
                if hasattr(event, 'candidates') and event.candidates:
                    if hasattr(event.candidates[0], 'content') and event.candidates[0].content:
                        if event.candidates[0].content.parts:
                            part = event.candidates[0].content.parts[0]

                            if part.inline_data:
                                async for inline_chunk in _yield_inline_image(part.inline_data):
                                    yield inline_chunk

                            if part.thought:
                                yield f"data: {json.dumps({'text': part.thought})}\n\n"

                            # Handle regular text content
                            if part.text:
                                text += event.text
                                yield f"data: {json.dumps({'text': event.text})}\n\n"

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
                                    async for status in handle_tool_call(function_call.name, function_call.args, mcp_manager):
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

                                    for result in json.loads(tool_result):
                                        if result["type"] == "text":
                                            function_response_parts.append(
                                                Part.from_function_response(
                                                    name=function_call.name,
                                                    response={"content": result}
                                                )
                                            )
                                        elif result["type"] == "image" and multimodal:
                                            # Base64エンコードされた文字列を取得
                                            base64_data_string = result["source"]["data"]
                                            decoded_data = base64.b64decode(base64_data_string)
                                            mime_type = result["source"]["media_type"]
                                            
                                            # sizeが20MB未満かどうか判定
                                            if len(decoded_data) > 20 * 1024 * 1024:
                                                log_info("Uploading image via Files API")
                                                uploaded_image = await upload_image_to_gemini(
                                                    decoded_data,
                                                    mime_type
                                                )
                                                function_response_parts.append(
                                                    Part.from_uri(
                                                        file_uri=uploaded_image.uri, 
                                                        mime_type=mime_type
                                                    )
                                                )
                                                images.append(uploaded_image)
                                            else:
                                                function_response_parts.append(
                                                    Part.from_bytes(
                                                        data=decoded_data,
                                                        mime_type=mime_type
                                                    )
                                                )


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

                                # Update running history with function call and response
                                running_history.append(function_call_content)
                                running_history.append(function_response_content)

                                # Change tool config to AUTO
                                tool_config = ToolConfig(
                                    function_calling_config=FunctionCallingConfig(mode='AUTO')
                                )
                                running_args["tool_config"] = tool_config

                                if tool_calls_count > 0:
                                    running_args["tools"] = [get_gemini_tool_definitions(canonical_tools=enabled_tools)]

                                tool_calls_count += 1

                                # Get new response incorporating tool results
                                response = await gemini_client.aio.models.generate_content_stream(
                                    model=model,
                                    contents=running_history,
                                    config=GenerateContentConfig(**running_args)
                                )
                                
                                break  # Break inner loop to start new response processing

                            if event.candidates:
                                if event.candidates[0].finish_reason:
                                    if event.usage_metadata:
                                        latest_usage = event.usage_metadata
                    
                else:
                    if hasattr(event, 'prompt_feedback'):
                        prompt_feedback: GenerateContentResponsePromptFeedback = event.prompt_feedback
                        if prompt_feedback:
                            yield f"data: {json.dumps({'text': prompt_feedback.model_dump_json()})}\n\n"

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


async def openai_stream_generator(
    response: Any,
    openai_client: AsyncOpenAI,
    openai_messages: List[Dict[str, Any]],
    completion_args: dict,
    mcp_manager: PolyMCPClient,
    enabled_tools: list[CanonicalToolDefinition],
    multimodal: bool = False
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
        # Create a running copy of completion args to maintain context
        running_args = completion_args.copy()
        
        while should_continue:  # Loop to handle recursive tool calls
            should_continue = False  # Reset flag, will be set to True if we need to continue
            log_info("Processing OpenAI stream")
            has_tool_call = False

            async for chunk in response:
                if chunk.choices:
                    delta = chunk.choices[0].delta

                    # Handle regular text content
                    if hasattr(delta, 'content') and delta.content is not None:
                        yield f"data: {json.dumps({'text': delta.content})}\n\n"
                        text_generated = True

                    # Handle tool calls
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        has_tool_call = True
                        for tool_call in delta.tool_calls:
                            index = tool_call.index
                            
                            if index not in tool_calls_buffer:
                                tool_calls_buffer[index] = tool_call
                                # First chunk of a tool call - we'll wait for full arguments before notifying
                                if tool_call.function and tool_call.function.name:
                                    yield f"data: {json.dumps({'type': 'tool_call_start', 'tool': tool_call.function.name, 'id': tool_call.id})}\n\n"
                            else:
                                # Accumulate arguments
                                current_args = tool_calls_buffer[index].function.arguments
                                new_args_chunk = tool_call.function.arguments

                                # Ensure both parts are treated as strings (empty if None) before concatenation
                                current_args_str = current_args if current_args is not None else ""
                                new_args_chunk_str = new_args_chunk if new_args_chunk is not None else ""
                                
                                # Perform safe concatenation
                                tool_calls_buffer[index].function.arguments = current_args_str + new_args_chunk_str
                            
                            # If we have complete arguments, execute the function
                            if (tool_call.function and tool_call.function.arguments and 
                                tool_call.function.arguments.endswith("}")):
                                complete_tool_call = tool_calls_buffer[index]

                                tool_name = complete_tool_call.function.name
                                
                                try:
                                    tool_input = json.loads(complete_tool_call.function.arguments)
                                    yield f"data: {json.dumps({'type': 'tool_call_start', 'tool': tool_name, 'input': tool_input})}\n\n"
                                    
                                    # Execute the tool
                                    tool_result = None
                                    async for status in handle_tool_call(tool_name, tool_input, mcp_manager):
                                        if status["type"] == "tool_execution_complete":
                                            tool_result = status["result"]
                                        else:
                                            # Forward status updates to frontend
                                            yield f"data: {json.dumps(status)}\n\n"

                                    if tool_result and openai_client:
                                        # Create a message with the tool call
                                        tool_use_message = {
                                            "role": "assistant",
                                            "content": None,
                                            "tool_calls": [
                                                {
                                                    "id": complete_tool_call.id,
                                                    "type": "function",
                                                    "function": {
                                                        "name": tool_name,
                                                        "arguments": complete_tool_call.function.arguments
                                                    }
                                                }
                                            ]
                                        }

                                        tool_result_text = ""
                                        tool_result_image = ""
                                        for result in json.loads(tool_result):
                                            if result["type"] == "text":
                                                tool_result_text = result
                                            elif result["type"] == "image":
                                                tool_result_image = f"data:{result['source']['media_type']};base64,{result['source']['data']}"
                                        
                                        if not tool_result_text:
                                            tool_result_text = "This tool did not return any text."
                                        
                                        # Create a message with the tool result
                                        tool_result_message = {
                                            "role": "tool",
                                            "tool_call_id": complete_tool_call.id,
                                            "name": tool_name,
                                            "content": [tool_result_text]
                                        }
                                        
                                        # Add messages to the running messages list
                                        running_args["messages"].append(tool_use_message)
                                        running_args["messages"].append(tool_result_message)

                                        if tool_result_image and multimodal:
                                            running_args["messages"].append({
                                                "role": "user",
                                                "name": tool_name,
                                                "content": [
                                                    {
                                                        "type": "image_url",
                                                        "image_url": {
                                                            "url": tool_result_image
                                                        }
                                                    }
                                                ]
                                            })

                                        # Make sure tools are included in the next request
                                        if tool_calls_count > 0 and "tools" in running_args:
                                            running_args["tools"] = get_tool_definitions(canonical_tools=enabled_tools)
                                            running_args["tool_choice"] = "auto"
                                        
                                        tool_calls_count += 1
                                        tool_calls_buffer = {}  # Reset buffer for next iteration
                                        
                                        # Get new response incorporating tool results
                                        response = await openai_client.chat.completions.create(**running_args)
                                        
                                        # Set flag to continue processing with the new response
                                        should_continue = True
                                        
                                        # Break the inner loop to start processing the new response
                                        break
                                        
                                except json.JSONDecodeError:
                                    log_error(f"Failed to parse tool input JSON: {complete_tool_call.function.arguments}")
                                    yield f"data: {json.dumps({'type': 'tool_call_end', 'tool': tool_name, 'input': {}})}\n\n"
                    

                # Check finish reason
                if chunk.choices and chunk.choices[0].finish_reason:
                    
                    if chunk.usage:
                        usage = await parse_usage(chunk.usage)
                        log_info("Token usage in OpenAI", usage)
                        yield f"data: {json.dumps(usage)}\n\n"

                    if chunk.choices[0].finish_reason == 'stop' and text_generated:
                        log_info("Stream generator ended normally")
                        break
                    elif chunk.choices[0].finish_reason == 'stop' and not text_generated:
                        log_info("Stream generator ended but no text generated")
                        break
                    elif chunk.choices[0].finish_reason == 'tool_calls':
                        log_info("Tool call completed, continuing with new request")
                        should_continue = True  # Ensure we continue processing for tool calls
                        break

                # If we need to continue with a new response due to tool call,
                # break the inner loop early
                if should_continue:
                    break

            # If we've completed processing and there are no more tool calls to handle
            if not should_continue:
                yield 'data: {"text": "[DONE]"}\n\n'
                break

    except Exception as e:
        log_error(f"Error in OpenAI stream generator: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


async def anthropic_stream_generator(
    response, 
    anthropic_client: AsyncAnthropic, 
    messages: List[Dict[str, Any]],
    params: dict,
    mcp_manager: PolyMCPClient,
    enabled_tools: list[CanonicalToolDefinition],
    multimodal: bool = False
) -> AsyncGenerator[str, None]:
    """
    Generate streaming response for Anthropic API.
    Handles both regular text responses and tool use cases with recursive tool handling.
    
    Args:
        response: Initial Anthropic API streaming response
        anthropic_client: Optional Anthropic client for tool result submission
        params: Original API request parameters for creating follow-up requests
        messages: Conversation history for context maintenance
        
    Yields:
        Streaming response data in SSE format
    """
    try:
        usage = {}
        tool_input_json = ""
        partial_text = ""
        current_tool_name = None
        current_tool_id = None
        should_continue = True
        tool_calls_count = 0
        # Create running params that will be updated with each tool call
        running_params = params.copy()

        while should_continue:
            should_continue = False  # Will be set to True if we need another iteration for tool execution
            log_info("Processing Anthropic stream")
            
            async for event in response:
                if event.type == "message_start":
                    message = event.message
                    if hasattr(message, 'usage'):
                        usage_start = await parse_usage_anthropic(message.usage)
                        log_info("Token usage in Anthropic in message_start", usage_start)
                        usage.update(usage_start)
                        
                elif event.type == "content_block_start":
                    if hasattr(event, 'content_block') and event.content_block:
                        if event.content_block.type == "thinking":
                            print(f"思考：{event.content_block.thinking}", end="", flush=True)
                        elif event.content_block.type == "text":
                            yield f"data: {json.dumps({'text': event.content_block.text})}\n\n"
                            partial_text += event.content_block.text
                        elif event.content_block.type == "tool_use":
                            # Tool use started - send tool call start event
                            current_tool_name = event.content_block.name
                            current_tool_id = event.content_block.id
                            tool_input_json = ""  # Reset the tool input JSON
                        
                elif event.type == "content_block_delta":
                    if event.delta.type == "thinking_delta":
                        print(f"{event.delta.thinking}", end="", flush=True)
                    elif event.delta.type == "text_delta":
                        yield f"data: {json.dumps({'text': event.delta.text})}\n\n"
                        partial_text += event.delta.text
                    elif event.delta.type == "input_json_delta":
                        # Accumulate the tool input JSON
                        tool_input_json += event.delta.partial_json
                        
                elif event.type == "content_block_stop":
                    if current_tool_name and current_tool_id:
                        # Tool use completed - try to parse the JSON and handle the tool call
                        try:
                            tool_input = json.loads(tool_input_json) if tool_input_json else {}
                            
                            # Execute the tool if we have a client to send results back to
                            if anthropic_client and current_tool_id and running_params is not None:
                                yield f"data: {json.dumps({'type': 'tool_call_start', 'tool': current_tool_name, 'id': current_tool_id})}\n\n"
                                log_info("Executing tool", {
                                    "tool": current_tool_name,
                                    "tool_use_id": current_tool_id
                                })
                                # Process the tool call
                                tool_result = None
                                async for status in handle_tool_call(current_tool_name, tool_input, mcp_manager):
                                    if status["type"] == "tool_execution_complete":
                                        tool_result = status["result"]
                                    else:
                                        # Forward status updates to frontend
                                        yield f"data: {json.dumps(status)}\n\n"
                                
                                if tool_result:
                                    # Use the running parameters which contain the full conversation context
                                    tool_use_content = []

                                    # if partial_text is not none, add text block to tool_use_content
                                    if partial_text:
                                        tool_use_content.append(
                                            {
                                                "type": "text",
                                                "text": partial_text
                                            }
                                        )

                                    # add tool_use block to tool_use_content
                                    tool_use_content.append(
                                        {
                                            "type": "tool_use",
                                            "id": current_tool_id,
                                            "name": current_tool_name,
                                            "input": tool_input
                                        }
                                    )

                                    tool_use_message = {
                                        "role": "assistant",
                                        "content": tool_use_content
                                    }

                                    # Create a user message with the tool result
                                    tool_result_message = {
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "tool_result",
                                                "tool_use_id": current_tool_id,
                                                "content": json.loads(tool_result)
                                            }
                                        ]
                                    }
                                    
                                    # Add messages to the running parameters
                                    running_params["messages"].append(tool_use_message)
                                    running_params["messages"].append(tool_result_message)
                                    
                                    # Make sure tools are included in the next request
                                    if tool_calls_count > 0 and "tools" in running_params:
                                        running_params["tools"] = get_anthropic_tool_definitions(canonical_tools=enabled_tools)
                                        
                                    log_info("Submitting tool result for continuation", {
                                        "tool": current_tool_name,
                                        "tool_use_id": current_tool_id
                                    })

                                    # log_info("Running Messages", running_params["messages"])

                                    # Create a new response with the tool result
                                    if "claude-3-7" in running_params["model"]:
                                        running_params["betas"] = ["token-efficient-tools-2025-02-19"]
                                        response = await anthropic_client.beta.messages.create(**running_params)
                                    else:
                                        response = await anthropic_client.messages.create(**running_params)
                                    
                                    # Set flag to continue processing with the new response
                                    should_continue = True
                                    tool_calls_count += 1
                                    
                                    # Reset tracking variables for next iteration
                                    current_tool_name = None
                                    current_tool_id = None

                                    if partial_text:
                                        # send line break to frontend
                                        yield f"data: {json.dumps({'text': '\n\n'})}\n\n"

                                    partial_text = ""

                                    # Break the inner loop to start processing the new response
                                    break
                            
                        except json.JSONDecodeError:
                            log_error(f"Failed to parse tool input JSON: {tool_input_json}")
                            yield f"data: {json.dumps({'type': 'tool_call_end', 'tool': current_tool_name, 'input': {}})}\n\n"
                        
                        # Reset tool tracking variables if not continuing
                        if not should_continue:
                            current_tool_name = None
                            current_tool_id = None
                        
                elif event.type == "message_delta":
                    if hasattr(event, 'usage'):
                        usage_delta = await parse_usage_anthropic(event.usage)
                        log_info("Token usage in Anthropic in message_delta", usage_delta)
                        usage.update(usage_delta)
                        yield f"data: {json.dumps(usage)}\n\n"
                        
                    # Forward stop reason to client
                    if hasattr(event, 'delta') and hasattr(event.delta, 'stop_reason'):
                        # stop_reason is not "tool_use" means the response is finished
                        if event.delta.stop_reason != "tool_use":
                            yield f"data: {json.dumps({'stop_reason': event.delta.stop_reason})}\n\n"
                        elif event.delta.stop_reason == "tool_use":
                            # in tool use, continue the loop
                            log_info("Tool use continues")
                            should_continue = True
                        
                elif event.type == "message_stop":
                    if not should_continue:  # Only emit DONE if we're not continuing with a tool result
                        yield f"data: {json.dumps({'text': '[DONE]'})}\n\n"
                        
                elif event.type == "ping":
                    yield ": ping\n\n"
                    
                elif event.type == "error":
                    raise Exception(event.error.message)
            
            # If we're not continuing due to a tool call, break the outer loop
            if not should_continue:
                break
                
    except Exception as e:
        log_error(f"Error in Anthropic stream generator: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n" 

async def anthropic_non_stream_generator(
    response, 
    anthropic_client: AsyncAnthropic, 
    messages: List[Dict[str, Any]],
    params: dict,
    mcp_manager: PolyMCPClient,
    enabled_tools: list[CanonicalToolDefinition],
    multimodal: bool = False
) -> AsyncGenerator[str, None]:
    """
    Generate non-streaming response for Anthropic API.
    Handles both regular text responses and tool use cases.
    
    Args:
        response: Initial Anthropic API response
        anthropic_client: Optional Anthropic client for tool result submission
        params: Original API request parameters for creating follow-up requests
        messages: Conversation history for context maintenance
        
    Yields:
        Response data in SSE format
    """
    try:
        content = response.content
        running_params = params.copy() if params else None
        
        # Check if there's a tool use in the response
        has_tool_use = False
        for block in content:
            if block.type == "tool_use":
                has_tool_use = True
                
                # Send the tool use start event
                yield f'data: {json.dumps({"type": "tool_call_start", "tool": block.name, "id": block.id})}\n\n'
                
                # Parse the tool input
                try:
                    tool_input = json.loads(block.input) if block.input else {}
                    yield f'data: {json.dumps({"type": "tool_call_end", "tool": block.name, "input": tool_input})}\n\n'
                    
                    # Execute the tool
                    tool_result = None
                    async for status in handle_tool_call(block.name, tool_input, mcp_manager):
                        yield f'data: {json.dumps(status)}\n\n'
                        if status["type"] == "tool_execution_complete":
                            tool_result = status["result"]
                    
                    if tool_result and anthropic_client and running_params:
                        # Get text content from the response to preserve in tool use message
                        text_content = ""
                        for text_block in content:
                            if text_block.type == "text":
                                text_content += text_block.text
                        
                        # Create assistant message with tool use
                        tool_use_message = {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "text",
                                    "text": text_content
                                },
                                {
                                    "type": "tool_use",
                                    "id": block.id,
                                    "name": block.name,
                                    "input": tool_input
                                }
                            ]
                        }
                        
                        # Create user message with tool result
                        tool_result_message = {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": tool_result
                                }
                            ]
                        }
                        
                        # Add messages to running params
                        if "messages" in running_params:
                            running_params["messages"].append(tool_use_message)
                            running_params["messages"].append(tool_result_message)
                        else:
                            running_params["messages"] = [tool_use_message, tool_result_message]
                        
                        # Continue the conversation with the tool result
                        tool_response = await anthropic_client.messages.create(**running_params)
                        
                        # Process the response content
                        for tool_block in tool_response.content:
                            if tool_block.type == "text":
                                yield f'data: {json.dumps({"text": tool_block.text})}\n\n'
                
                except Exception as e:
                    log_error(f"Error handling tool use: {str(e)}")
                    yield f'data: {json.dumps({"error": str(e)})}\n\n'
                
                break  # Only handle the first tool use in non-streaming mode
        
        # If no tool use, just return the text content
        if not has_tool_use:
            for block in content:
                if block.type == "text":
                    yield f'data: {json.dumps({"text": block.text})}\n\n'
                elif block.type == "thinking":
                    if block.thinking:
                        print(f"思考：{block.thinking}")

        # Include usage information if available
        if hasattr(response, 'usage'):
            usage = await parse_usage_anthropic(response.usage)
            yield f"data: {json.dumps(usage)}\n\n"

        yield 'data: {"text": "[DONE]"}\n\n'
        
    except Exception as e:
        log_error(f"Error in Anthropic non-stream generator: {str(e)}")
        yield f'data: {json.dumps({"error": str(e)})}\n\n' 


async def gemini_non_stream_generator(
    response: Any,
    gemini_client: Client,
    model: str,
    history: list[Content],
    completion_args: dict,
    images: list,
    mcp_manager: PolyMCPClient,
    enabled_tools: list[CanonicalToolDefinition],
    multimodal: bool = False
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
        # Make a copy of history and completion_args to maintain context
        running_history = history.copy()
        running_args = completion_args.copy()
        
        # Handle function calls if present
        if hasattr(response, 'function_calls'):
            for function_call in response.function_calls:
                # Notify about tool call start
                yield f"data: {json.dumps({'type': 'tool_call_start', 'tool': function_call.name})}\n\n"
                
                # Handle the tool call
                tool_result = None
                async for status in handle_tool_call(function_call.name, function_call.args, mcp_manager):
                    if status["type"] == "tool_execution_complete":
                        tool_result = status["result"]
                    else:
                        # Forward status updates to frontend
                        yield f"data: {json.dumps(status)}\n\n"
                
                # Create function call content
                function_call_part = Part.from_function_call(
                    name=function_call.name,
                    args=function_call.args
                )
                function_call_content = Content(
                    role="model",
                    parts=[function_call_part]
                )
                running_history.append(function_call_content)
                
                # Create function response content with the tool result
                function_response_part = Part.from_function_response(
                    name=function_call.name,
                    response={"result": tool_result}
                )
                function_response_content = Content(
                    role="user", 
                    parts=[function_response_part]
                )
                running_history.append(function_response_content)
                
                # Change tool config to AUTO
                tool_config = ToolConfig(
                    function_calling_config=FunctionCallingConfig(mode='AUTO')
                )
                running_args["tool_config"] = tool_config

                # Create new chat with updated history
                chat = gemini_client.aio.chats.create(
                    history=running_history,
                    model=model,
                    config=GenerateContentConfig(**running_args)
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


async def openai_non_stream_generator(
    openai_client: AsyncOpenAI,
    completion_args: dict,
    openai_messages: list,
    mcp_manager: PolyMCPClient,
    enabled_tools: list[CanonicalToolDefinition],
    multimodal: bool = False
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
    try:
        # Create a running copy of completion args to maintain context
        running_args = completion_args.copy()
        
        response = await openai_client.chat.completions.create(**running_args)
        
        # Check if tool calls are present in the response
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                yield f"data: {json.dumps({'type': 'tool_call_start', 'tool': tool_call.function.name, 'id': tool_call.id})}\n\n"
                
                # Parse the tool input
                try:
                    tool_input = json.loads(tool_call.function.arguments)
                    yield f"data: {json.dumps({'type': 'tool_call_end', 'tool': tool_call.function.name, 'input': tool_input})}\n\n"
                    
                    # Execute the tool
                    tool_result = None
                    async for status in handle_tool_call(tool_call.function.name, tool_input, mcp_manager):
                        yield f"data: {json.dumps(status)}\n\n"
                        if status["type"] == "tool_execution_complete":
                            tool_result = status["result"]
                    
                    if tool_result:
                        # Create a message with the tool call
                        tool_use_message = {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tool_call.id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_call.function.name,
                                        "arguments": tool_call.function.arguments
                                    }
                                }
                            ]
                        }
                        
                        # Create a message with the tool result
                        tool_result_message = {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": tool_result
                        }
                        
                        # Add messages to the running messages
                        running_args["messages"].append(tool_use_message)
                        running_args["messages"].append(tool_result_message)    
                        
                        # Make sure tools are included in the next request
                        running_args["tools"] = get_tool_definitions(canonical_tools=enabled_tools)
                        running_args["tool_choice"] = "auto"
                        
                        # Continue the conversation with the tool result
                        next_response = await openai_client.chat.completions.create(**running_args)
                        
                        # Output the final text response
                        if next_response.choices[0].message.content:
                            yield f'data: {json.dumps({"text": next_response.choices[0].message.content})}\n\n'
                            
                        # Return usage info if available
                        if next_response.usage:
                            usage = await parse_usage(next_response.usage)
                            log_info("Token usage in OpenAI", usage)
                            yield f"data: {json.dumps(usage)}\n\n"
                            
                except json.JSONDecodeError as e:
                    log_error(f"Failed to parse tool arguments: {str(e)}")
                    yield f"data: {json.dumps({'error': f'Failed to parse tool arguments: {str(e)}'})}\n\n"
                
                # Only handle the first tool call in non-streaming mode
                break
        
        # If no tool calls, just return the regular content
        elif response.choices[0].message.content:
            yield f'data: {json.dumps({"text": response.choices[0].message.content})}\n\n'
            
            # Return usage info if available
            if response.usage:
                usage = await parse_usage(response.usage)
                log_info("Token usage in OpenAI", usage)
                yield f"data: {json.dumps(usage)}\n\n"
        
        yield 'data: {"text": "[DONE]"}\n\n'
        
    except Exception as e:
        log_error(f"Error in OpenAI non-stream generator: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

