from typing import Any, Dict, Optional
import google.generativeai as genai
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import json

from app.utils.stream_generators import (
    gemini_stream_generator,
    openai_stream_generator,
    anthropic_stream_generator
)
from app.utils.message_utils import prepare_api_messages, prepare_openai_messages, prepare_anthropic_messages
from app.utils.image_utils import upload_image_to_gemini
from app.models.models import ChatRequest
from app.utils.tool_utils import get_tool_definitions
from app.utils.tool_handlers import handle_tool_call, parse_usage

class ChatHandler:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _handle_openai_non_stream(
        self,
        openai: AsyncOpenAI,
        completion_args: dict,
        model: str,
        openai_messages: list
    ) -> Any:
        """
        Common processing for non-streaming OpenAI API calls.
        This function also handles tool_calls if present in the response.
        Returns the response as a streaming response for consistency with streaming mode.
        
        Args:
            openai: The AsyncOpenAI client instance.
            completion_args: The arguments to pass to the API call.
            model: The full model string (e.g., "openai-gpt4").
            openai_messages: Formatted conversation messages.
        
        Returns:
            A StreamingResponse containing the response message.
        """
        response = await openai.chat.completions.create(**completion_args)

        async def generate_non_stream_response(response):
            # Check if a tool_call is present in the response
            while response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]

                yield f"data: {json.dumps({'type': 'tool_call_start', 'tool': tool_call.function.name})}\n\n"

                # Handle the tool call using common handler and yield status updates
                async for status in handle_tool_call(tool_call, openai_messages):
                    yield status
                
                completion_args['messages'] = openai_messages

                # Get final response incorporating tool results with tools enabled
                final_response = await openai.chat.completions.create(
                    **completion_args,
                )
                response = final_response  # Update response for next iteration check
            
            # After all tool calls are processed, return the final content
            if response.choices[0].message.content:
                yield f'data: {json.dumps({"text": response.choices[0].message.content})}\n\n'

            if response.usage:
                usage = parse_usage(response.usage)
                yield f"data: {json.dumps(usage)}\n\n"
            
            yield 'data: {"text": "[DONE]"}\n\n'

        return StreamingResponse(
            generate_non_stream_response(response),
            media_type="text/event-stream"
        )

    async def handle_openai(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str,
        websearch: bool = True,
        reasoning_effort: Optional[str] = None,
        is_reasoning_supported: bool = False
    ) -> Any:
        """Handle OpenAI API requests with optional function calling.
        
        If a BadRequest error indicates that stream mode is unsupported,
        the generation falls back to non-streaming mode using common logic.
        """
        openai = AsyncOpenAI(api_key=self.api_key)
        openai_messages = prepare_openai_messages(system, messages)

        completion_args = {
            "model": model[7:],  # Remove 'openai-' prefix
            "messages": openai_messages,
            "max_completion_tokens": max_tokens,
            "stream": stream,
        }
        
        if temperature is not None and not is_reasoning_supported:
            completion_args["temperature"] = temperature
            
        if is_reasoning_supported and reasoning_effort:
            completion_args["reasoning_effort"] = reasoning_effort

        if websearch:
            completion_args["tools"] = get_tool_definitions()

        # If streaming is requested, try using stream mode.
        if stream:
            completion_args["stream_options"] = { "include_usage": True }
            try:
                response = await openai.chat.completions.create(**completion_args)
                return StreamingResponse(
                    openai_stream_generator(
                        response,
                        openai_client=openai,
                        messages=openai_messages,
                        completion_args=completion_args
                    ),
                    media_type="text/event-stream"
                )
            except Exception as e:
                # If the error indicates that stream mode is unsupported, fall back.
                if "Unsupported value: 'stream'" in str(e):
                    completion_args["stream"] = False
                    completion_args.pop("stream_options")
                    # Delegate non-streamed handling to the common function.
                    return await self._handle_openai_non_stream(
                        openai, completion_args, model, openai_messages
                    )
                else:
                    raise e
        else:
            completion_args["stream"] = False
            # For explicit non-stream requests, delegate to the common function.
            return await self._handle_openai_non_stream(
                openai, completion_args, model, openai_messages
            )

    async def handle_anthropic(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str,
        multimodal: bool = False
    ) -> Any:
        """Handle Anthropic API requests"""
        anthropic = AsyncAnthropic(api_key=self.api_key)
        anthropic_messages = prepare_anthropic_messages(messages)
        
        response = await anthropic.messages.create(
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"}
                },
            ],
            model=model,
            messages=anthropic_messages,
            max_tokens=max_tokens,
            stream=stream,
            temperature=temperature
        )

        if stream:
            return StreamingResponse(
                anthropic_stream_generator(response),
                media_type="text/event-stream"
            )
        else:
            async def generate_non_stream_response():
                yield f'data: {json.dumps({"text": response.content[0].text})}\n\n'
                yield 'data: {"text": "[DONE]"}\n\n'

            return StreamingResponse(
                generate_non_stream_response(),
                media_type="text/event-stream"
            )

    async def handle_gemini(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str
    ) -> Any:
        """Handle Gemini API requests"""
        genai.configure(api_key=self.api_key)
        
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "top_p": 0.95,
            "top_k": 40,
            "response_mime_type": "text/plain",
        }

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]

        model_instance = genai.GenerativeModel(
            model_name=model,
            safety_settings=safety_settings,
            generation_config=generation_config,
            system_instruction=[system]
        )

        # Process history and current message
        images = []
        history = []
        for message in messages[:-1]:
            parts = []
            role = "model" if message["role"] == "assistant" else message["role"]
            for content in message["content"]:
                if content["type"] == "image":
                    uploaded_image = await upload_image_to_gemini(
                        content["source"]["data"],
                        content["source"]["media_type"]
                    )
                    parts.append(uploaded_image.uri)
                    images.append(uploaded_image)
                elif content["type"] == "text":
                    parts.append(content["text"])
            history.append({"role": role, "parts": parts})

        chat = model_instance.start_chat(history=history)
        
        # Process latest message
        latest_message = messages[-1]
        latest_parts = []
        for content in latest_message["content"]:
            if content["type"] == "text":
                latest_parts.append(content["text"])
            elif content["type"] == "image":
                uploaded_image = await upload_image_to_gemini(
                    content["source"]["data"],
                    content["source"]["media_type"]
                )
                latest_parts.append(uploaded_image)
                images.append(uploaded_image)
        response = await chat.send_message_async(
            content=latest_parts,
            stream=stream,
            safety_settings=safety_settings
        )

        for image in images:
            try:
                genai.delete_file(image.name)
            except Exception as e:
                print(f"Error deleting image: {e}")

        if stream:
            return StreamingResponse(
                gemini_stream_generator(response),
                media_type="text/event-stream"
            )
        else:
            async def generate_non_stream_response():
                yield f'data: {json.dumps({"text": response.text})}\n\n'
                yield 'data: {"text": "[DONE]"}\n\n'

            return StreamingResponse(
                generate_non_stream_response(),
                media_type="text/event-stream"
            )

    async def handle_deepseek(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str
    ) -> Any:
        """Handle Deepseek API requests"""
        deepseek = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )

        deepseek_messages = prepare_openai_messages(system, messages)

        completion_args = {
            "model": model,
            "messages": deepseek_messages,
            "max_tokens": max_tokens,
            "stream": stream,
            "temperature": temperature
        }

        response = await deepseek.chat.completions.create(**completion_args)

        if stream:
            completion_args["stream_options"] = {"include_usage": True}
            return StreamingResponse(
                openai_stream_generator(
                    response,
                    openai_client=deepseek,
                    messages=deepseek_messages,
                    model=model
                ),
                media_type="text/event-stream"
            )
        else:
            async def generate_non_stream_response():
                yield f'data: {json.dumps({"text": response.choices[0].message.content})}\n\n'
                yield 'data: {"text": "[DONE]"}\n\n'

            return StreamingResponse(
                generate_non_stream_response(),
                media_type="text/event-stream"
            )

    async def handle_openrouter(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str
    ) -> Any:
        """Handle OpenRouter API requests"""
        openrouter = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1"
        )

        openrouter_messages = prepare_openai_messages(system, messages)

        completion_args = {
            "model": model,
            "messages": openrouter_messages,
            "max_tokens": max_tokens,
            "stream": stream,
            "temperature": temperature
        }

        response = await openrouter.chat.completions.create(**completion_args)

        if stream:
            completion_args["stream_options"] = {"include_usage": True}
            return StreamingResponse(
                openai_stream_generator(
                    response,
                    openai_client=openrouter,
                    messages=openrouter_messages,
                    model=model
                ),
                media_type="text/event-stream"
            )
        else:
            async def generate_non_stream_response():
                yield f'data: {json.dumps({"text": response.choices[0].message.content})}\n\n'
                yield 'data: {"text": "[DONE]"}\n\n'

            return StreamingResponse(
                generate_non_stream_response(),
                media_type="text/event-stream"
            ) 

    async def handle_chat_request(self, chat_request: ChatRequest) -> Any:
        """
        Main entry point for handling chat requests
        
        Args:
            chat_request: ChatRequest object containing all request parameters
            
        Returns:
            Appropriate response based on the model and streaming settings
        """
        try:
            messages = await prepare_api_messages(chat_request.messages, multimodal=chat_request.multimodal)
            
            if chat_request.model.startswith('openai-'):
                return await self.handle_openai(
                    model=chat_request.model,
                    messages=messages,
                    max_tokens=chat_request.maxTokens,
                    temperature=chat_request.temperature,
                    stream=chat_request.stream,
                    system=chat_request.system,
                    websearch=chat_request.websearch,
                    reasoning_effort=chat_request.reasoningEffort,
                    is_reasoning_supported=chat_request.isReasoningSupported,
                )
            elif chat_request.model.startswith('deepseek-'):
                return await self.handle_deepseek(
                    model=chat_request.model,
                    messages=messages,
                    max_tokens=chat_request.maxTokens,
                    temperature=chat_request.temperature,
                    stream=chat_request.stream,
                    system=chat_request.system
                )
            elif chat_request.model.startswith('gemini-'):
                return await self.handle_gemini(
                    model=chat_request.model,
                    messages=messages,
                    max_tokens=chat_request.maxTokens,
                    temperature=chat_request.temperature,
                    stream=chat_request.stream,
                    system=chat_request.system
                )
            elif "/" in chat_request.model:  # OpenRouter models
                return await self.handle_openrouter(
                    model=chat_request.model,
                    messages=messages,
                    max_tokens=chat_request.maxTokens,
                    temperature=chat_request.temperature,
                    stream=chat_request.stream,
                    system=chat_request.system
                )
            else:  # Anthropic models
                return await self.handle_anthropic(
                    model=chat_request.model,
                    messages=messages,
                    max_tokens=chat_request.maxTokens,
                    temperature=chat_request.temperature,
                    stream=chat_request.stream,
                    system=chat_request.system
                )
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
