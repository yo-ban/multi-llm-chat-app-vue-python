from typing import Any, Dict, Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import json
from google import genai
from google.genai.types import (
    ToolConfig,
    FunctionCallingConfig,
    AutomaticFunctionCallingConfig,
    GenerateContentConfig,
    SafetySetting,
    HarmCategory,
    HarmBlockThreshold,
    Content,
    Part,
    ThinkingConfig
)

from app.message_utils.response_generator import (
    gemini_stream_generator,
    gemini_non_stream_generator,
    openai_stream_generator,
    openai_non_stream_generator,
    anthropic_stream_generator,
    anthropic_non_stream_generator
)
from app.message_utils.messages_preparer import (
    prepare_api_messages, 
    prepare_openai_messages, 
    prepare_anthropic_messages, 
)

from app.misc_utils.image_utils import upload_image_to_gemini
from app.models.models import ChatRequest
from app.function_calling.definitions import get_tool_definitions, get_gemini_tool_definitions, get_anthropic_tool_definitions
from app.function_calling.constants import TOOL_USE_INSTRUCTION
from app.logger.logging_utils import log_info, log_error, log_warning

class ChatHandler:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def handle_openai(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str,
        websearch: bool = False,
        reasoning_effort: Optional[str] = None,
        is_reasoning_supported: bool = False
    ) -> Any:
        """Handle OpenAI API requests with optional function calling.
        
        If a BadRequest error indicates that stream mode is unsupported,
        the generation falls back to non-streaming mode using common logic.
        """
        openai = AsyncOpenAI(api_key=self.api_key)
        openai_messages = await prepare_openai_messages(system, messages)

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
            completion_args["tool_choice"] = "required"

        # If streaming is requested, try using stream mode.
        if stream:
            completion_args["stream_options"] = { "include_usage": True }
            try:
                response = await openai.chat.completions.create(**completion_args)
                return StreamingResponse(
                    openai_stream_generator(
                        response,
                        openai_client=openai,
                        openai_messages=openai_messages,
                        completion_args=completion_args
                    ),
                    media_type="text/event-stream"
                )
            except Exception as e:
                # If the error indicates that stream mode is unsupported, fall back.
                if "Unsupported value: 'stream'" in str(e):
                    log_warning("Stream mode is unsupported, falling back to non-streaming mode")
                    completion_args["stream"] = False
                    completion_args.pop("stream_options")
                    # Delegate non-streamed handling to the common function.
                    return StreamingResponse(
                        openai_non_stream_generator(
                            openai_client=openai, 
                            completion_args=completion_args, 
                            openai_messages=openai_messages
                        ),
                        media_type="text/event-stream"
                    )
                else:
                    raise e
        else:
            completion_args["stream"] = False
            # For explicit non-stream requests, delegate to the common function.
            return StreamingResponse(
                openai_non_stream_generator(
                    openai_client=openai, 
                    completion_args=completion_args, 
                    openai_messages=openai_messages
                ),
                media_type="text/event-stream"
            )

    async def handle_anthropic(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str,
        websearch: bool = False,
        reasoning_effort: Optional[str] = None,
        is_reasoning_supported: bool = False
    ) -> Any:
        """Handle Anthropic API requests"""
        anthropic = AsyncAnthropic(api_key=self.api_key)
        anthropic_messages = await prepare_anthropic_messages(messages)

        params = {
            "system": [
                {
                    "type": "text",
                    "text": system,
                }
            ],
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "stream": stream,
            "temperature": temperature
        }

        if is_reasoning_supported:
            if reasoning_effort == "low":
                budget_tokens = 6000
            elif reasoning_effort == "medium":
                budget_tokens = 10000
            elif reasoning_effort == "high":
                budget_tokens = 14000
                
            model = model.replace("-thinking", "")

            params["model"] = model

            params["thinking"] = {
                "type": "enabled",
                "budget_tokens": budget_tokens
            }

        response = None

        if websearch:
            params["tools"] = get_anthropic_tool_definitions()
            if "claude-3-7" in model:
                params["betas"] = ["token-efficient-tools-2025-02-19"]
                response = await anthropic.beta.messages.create(**params)
            else:
                response = await anthropic.messages.create(**params)
        else:
            response = await anthropic.messages.create(**params)

        if stream:
            return StreamingResponse(
                anthropic_stream_generator(
                    response=response,
                    anthropic_client=anthropic,
                    messages=anthropic_messages,
                    params=params
                ),
                media_type="text/event-stream"
            )
        else:
            return StreamingResponse(
                anthropic_non_stream_generator(
                    response=response,
                    anthropic_client=anthropic,
                    params=params,
                    messages=anthropic_messages
                ),
                media_type="text/event-stream"
            )

    async def handle_gemini(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str,
        websearch: bool = False,
        reasoning_effort: Optional[str] = None,
        is_reasoning_supported: bool = False,
        image_generation: bool = False
    ) -> Any:
        """Handle Gemini API requests using the new client"""
        client = genai.Client(api_key=self.api_key)
        
        safety_settings = [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.OFF,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=HarmBlockThreshold.OFF
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.OFF
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=HarmBlockThreshold.OFF
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                threshold=HarmBlockThreshold.OFF
            )
        ]

        completion_args = {
            "response_modalities": ["TEXT"],
            "safety_settings": safety_settings,
            "system_instruction": system,
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": max_tokens,
            "response_mime_type": "text/plain"
        }

        # if is_reasoning_supported:
        #     completion_args["thinking_config"] = ThinkingConfig(
        #         include_thoughts=True
        #     )

        if image_generation:
            completion_args["response_modalities"] = [
                "IMAGE",
                "TEXT"
            ]
            # remove system instruction
            completion_args.pop("system_instruction")

        if websearch:
            tool_config = ToolConfig(
                function_calling_config=FunctionCallingConfig(mode='ANY')
            )
            automatic_function_calling = AutomaticFunctionCallingConfig(
                disable=True,
                ignore_call_history=True
            )
            completion_args["tools"] = [get_gemini_tool_definitions()]
            completion_args["tool_config"] = tool_config
            completion_args["automatic_function_calling"] = automatic_function_calling

        generation_config = GenerateContentConfig(**completion_args)

        # Process history and current message
        history: list[Content] = []
        images = []
        for message in messages[:-1]:
            parts = []
            role = "model" if message["role"] == "assistant" else message["role"]
            for content in message["content"]:
                if content["type"] == "image":
                    uploaded_image = await upload_image_to_gemini(
                        content["source"]["data"],
                        content["source"]["media_type"]
                    )
                    parts.append(Part.from_uri(file_uri=uploaded_image.uri, mime_type=content["source"]["media_type"]))
                    images.append(uploaded_image)
                if content["type"] == "text":
                    parts.append(Part.from_text(text=content["text"]))
            history.append(Content(parts=parts, role=role))

        # Process latest message
        latest_message = messages[-1]
        latest_parts = []
        for content in latest_message["content"]:
            if content["type"] == "text":
                latest_parts.append(Part.from_text(text=content["text"]))
            if content["type"] == "image":
                uploaded_image = await upload_image_to_gemini(
                    content["source"]["data"],
                    content["source"]["media_type"]
                )
                latest_parts.append(Part.from_uri(file_uri=uploaded_image.uri, mime_type=content["source"]["media_type"]))
                images.append(uploaded_image)

        latest_content = Content(parts=latest_parts, role="user")

        # Add latest content to history
        history.append(latest_content)
        

        if stream:
            response = await client.aio.models.generate_content_stream(
                model=model,
                contents=history,
                config=generation_config
            )

            return StreamingResponse(
                gemini_stream_generator(
                    response,
                    gemini_client=client, 
                    model=model,
                    history=history,
                    completion_args=completion_args,
                    images=images
                ),
                media_type="text/event-stream"
            )
        else:
            response = await client.aio.models.generate_content(
                model=model,
                contents=history,
                config=generation_config
            )

            return StreamingResponse(
                gemini_non_stream_generator(
                    response,
                    gemini_client=client,
                    model=model,
                    history=history,
                    completion_args=completion_args
                ),
                media_type="text/event-stream"
            )

    async def handle_openrouter(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str,
        websearch: bool = False,
        reasoning_effort: Optional[str] = None,
        is_reasoning_supported: bool = False
    ) -> Any:
        """Handle OpenRouter API requests"""
        openrouter = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1"
        )

        openrouter_messages = await prepare_openai_messages(system, messages)

        completion_args = {
            "model": model,
            "messages": openrouter_messages,
            "max_tokens": max_tokens,
            "stream": stream,
            "temperature": temperature,
            "extra_body": { 
                "provider": {
                    "order": [
                        "DeepInfra",
                        "Parasail"
                    ],
                    "ignore": [
                        "Hyperbolic"
                    ]
                }
            }
        }

        if temperature is not None and not is_reasoning_supported:
            completion_args["temperature"] = temperature
            
        if is_reasoning_supported and reasoning_effort:
            completion_args["reasoning_effort"] = reasoning_effort

        if websearch:
            completion_args["tools"] = get_tool_definitions()
            completion_args["tool_choice"] = "required"

        response = await openrouter.chat.completions.create(**completion_args)

        if stream:
            completion_args["stream_options"] = {"include_usage": True}
            return StreamingResponse(
                openai_stream_generator(
                    response,
                    openai_client=openrouter,
                    openai_messages=openrouter_messages,
                    completion_args=completion_args
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

            if chat_request.websearch:
                system = f"{chat_request.system}\n\n{TOOL_USE_INSTRUCTION}"
            else:
                system = chat_request.system
            
            if chat_request.model.startswith('openai-'):
                return await self.handle_openai(
                    model=chat_request.model,
                    messages=messages,
                    max_tokens=chat_request.maxTokens,
                    temperature=chat_request.temperature,
                    stream=chat_request.stream,
                    system=system,
                    websearch=chat_request.websearch,
                    reasoning_effort=chat_request.reasoningEffort,
                    is_reasoning_supported=chat_request.isReasoningSupported,
                )
            elif chat_request.model.startswith('gemini-'):
                return await self.handle_gemini(
                    model=chat_request.model,
                    messages=messages,
                    max_tokens=chat_request.maxTokens,
                    temperature=chat_request.temperature,
                    stream=chat_request.stream,
                    system=system,
                    websearch=chat_request.websearch,
                    image_generation=chat_request.imageGeneration,
                    is_reasoning_supported=chat_request.isReasoningSupported,
                )
            elif "/" in chat_request.model:  # OpenRouter models
                return await self.handle_openrouter(
                    model=chat_request.model,
                    messages=messages,
                    max_tokens=chat_request.maxTokens,
                    temperature=chat_request.temperature,
                    stream=chat_request.stream,
                    system=system,
                    websearch=chat_request.websearch,
                    reasoning_effort=chat_request.reasoningEffort,
                    is_reasoning_supported=chat_request.isReasoningSupported
                )
            else:  # Anthropic models
                return await self.handle_anthropic(
                    model=chat_request.model,
                    messages=messages,
                    max_tokens=chat_request.maxTokens,
                    temperature=chat_request.temperature,
                    stream=chat_request.stream,
                    system=system,
                    websearch=chat_request.websearch,
                    reasoning_effort=chat_request.reasoningEffort,
                    is_reasoning_supported=chat_request.isReasoningSupported
                )
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
