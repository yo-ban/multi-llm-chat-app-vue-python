import json
from typing import AsyncGenerator, Any, Dict, List
from openai import AsyncOpenAI
from ..utils.search_utils import web_search
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

    def _parse_usage(usage: Any) -> Dict[str, Any]:
        if usage.completion_tokens:
            completion_usage = usage.completion_tokens
        else:
            completion_usage = 0
        
        if usage.prompt_tokens:
            prompt_usage = usage.prompt_tokens
        else:
            prompt_usage = 0
        
        if usage.completion_tokens_details:
            if usage.completion_tokens_details.reasoning_tokens:
                reasoning_usage = usage.completion_tokens_details.reasoning_tokens
            else:
                reasoning_usage = 0
        else:
            reasoning_usage = 0

        return {
            "completion_usage": completion_usage,
            "prompt_usage": prompt_usage,
            "reasoning_usage": reasoning_usage
        }

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
                            args = json.loads(complete_call.function.arguments)

                            query = args.get("query")
                            num_results = args.get("num_results", 5)

                            if complete_call.function.name == "web_search" and query:
                                results = await web_search(query, num_results)
                                # yield f"data: {json.dumps({'type': 'tool_result', 'results': [r.model_dump() for r in results]})}\n\n"
                                
                                if openai_client and messages and model:
                                    # Add results to messages for context
                                    messages.append({
                                        "role": "assistant",
                                        "content": None,
                                        "tool_calls": [complete_call.model_dump()]
                                    })
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": complete_call.id,
                                        "content": json.dumps([r.model_dump() for r in results])
                                    })
                                    
                                    # Get final response incorporating search results
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
                                            usage = _parse_usage(final_chunk.usage)
                                            log_info(f"Completion Usage: {usage['completion_usage']}, Prompt Usage: {usage['prompt_usage']}, Reasoning Usage: {usage['reasoning_usage']}")
                                            yield f"data: {json.dumps(usage)}\n\n"
                
                # Handle regular text content
                elif delta.content:
                    yield f"data: {json.dumps({'text': delta.content})}\n\n"

            if chunk.usage:
                usage = _parse_usage(chunk.usage)
                log_info(f"Completion Usage: {usage['completion_usage']}, Prompt Usage: {usage['prompt_usage']}, Reasoning Usage: {usage['reasoning_usage']}")
                yield f"data: {json.dumps(usage)}\n\n"

        yield f"data: {json.dumps({'text': '[DONE]'})}\n\n"
        
    except Exception as e:
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