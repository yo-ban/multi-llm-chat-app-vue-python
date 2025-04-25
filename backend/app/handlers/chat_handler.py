from typing import Any, Dict, Optional, List
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import base64
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
    ThinkingConfig,
)

from sqlalchemy.orm import Session # DBセッション用
from app.application.settings.service import SettingsService # 設定サービス用

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

from poly_mcp_client import PolyMCPClient
from poly_mcp_client.models import CanonicalToolDefinition # 型ヒントのため

from app.misc_utils.image_utils import upload_image_to_gemini
from app.domain.messages.schemas import ChatRequest
from app.function_calling.definitions import (
    get_tool_definitions, 
    get_gemini_tool_definitions, 
    get_anthropic_tool_definitions, 
    get_available_tools as get_builtin_tool_functions, # built-in 関数取得用
    generate_tool_definition as generate_builtin_tool_definition # built-in 定義生成用
)
from app.function_calling.constants import TOOL_USE_INSTRUCTION
from app.logger.logging_utils import log_info, log_error, log_warning

# 定数 (仮ユーザーID)
TEMP_USER_ID = 1


class ChatHandler:
    def __init__(self, api_key: str, settings_service: SettingsService):
        self.api_key = api_key
        self.settings_service = settings_service
        self.handlers = {
            'openai': self.handle_openai,
            'google': self.handle_gemini,
            'openrouter': self.handle_openrouter,
            'xai': self.handle_xai,
            'anthropic': self.handle_anthropic
        }

    async def handle_openai(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str,
        mcp_manager: PolyMCPClient, # MCP Managerを追加
        enabled_tools: Optional[List[CanonicalToolDefinition]] = None, # MCPツール定義を追加
        toolUse: bool = False,        
        reasoning_effort: Optional[str] = None,
        is_reasoning_supported: bool = False,
        reasoning_parameter_type: Optional[str] = None,
        budget_tokens: Optional[int] = None,
        multimodal: bool = False,
        image_generation: bool = False
    ) -> Any:
        """Handle OpenAI API requests with optional function calling.
        
        If a BadRequest error indicates that stream mode is unsupported,
        the generation falls back to non-streaming mode using common logic.
        """
        openai = AsyncOpenAI(api_key=self.api_key)
        openai_messages = await prepare_openai_messages(system, messages)

        completion_args = {
            "model": model,
            "messages": openai_messages,
            "max_completion_tokens": max_tokens,
            "stream": stream,
        }

        if is_reasoning_supported:
            if reasoning_parameter_type == "effort" and reasoning_effort:
                completion_args["reasoning_effort"] = reasoning_effort
        else:
            completion_args["temperature"] = temperature

        if toolUse and enabled_tools:
            completion_args["tools"] = get_tool_definitions(canonical_tools=enabled_tools)
            completion_args["tool_choice"] = "required"
        elif toolUse:
            log_warning("Tool use requested, but no MCP tools are available/enabled.")

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
                        completion_args=completion_args,
                        multimodal=multimodal,
                        mcp_manager=mcp_manager,
                        enabled_tools=enabled_tools
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
                            openai_messages=openai_messages,
                            multimodal=multimodal,
                            mcp_manager=mcp_manager,
                            enabled_tools=enabled_tools
                        ),
                        media_type="text/event-stream"
                    )
                else:
                    log_error(f"OpenAI API error (stream): {e}", {"model": model, "stream": True})
                    raise e
        else:
            completion_args["stream"] = False
            try:
                return StreamingResponse(
                    openai_non_stream_generator(
                        openai_client=openai,
                        completion_args=completion_args,
                        openai_messages=openai_messages,
                        multimodal=multimodal,
                        mcp_manager=mcp_manager,
                        enabled_tools=enabled_tools
                    ),
                    media_type="text/event-stream"
                )
            except Exception as e:
                log_error(f"OpenAI API error (non-stream): {e}", {"model": model, "stream": False})
                raise e

    async def handle_anthropic(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str,
        mcp_manager: PolyMCPClient, # MCP Managerを追加
        enabled_tools: Optional[List[CanonicalToolDefinition]] = None, # MCPツール定義を追加
        toolUse: bool = False,
        reasoning_effort: Optional[str] = None,
        is_reasoning_supported: bool = False,
        reasoning_parameter_type: Optional[str] = None,
        budget_tokens: Optional[int] = None,
        multimodal: bool = False,
        image_generation: bool = False
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
            if reasoning_parameter_type == "budget" and budget_tokens:

                params["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": budget_tokens
                }

            model = model.replace("-thinking", "")
            params["model"] = model

        response = None

        if toolUse and enabled_tools:
            params["tools"] = get_anthropic_tool_definitions(canonical_tools=enabled_tools)
            if "claude-3-7" in model:
                params["betas"] = ["token-efficient-tools-2025-02-19"]
                response = await anthropic.beta.messages.create(**params)
            else:
                response = await anthropic.messages.create(**params)
        elif toolUse:
            log_warning("Tool use requested, but no MCP tools are available/enabled.")
            response = await anthropic.messages.create(**params)
        else:
            response = await anthropic.messages.create(**params)

        if stream:
            try:
                return StreamingResponse(
                    anthropic_stream_generator(
                        response=response,
                        anthropic_client=anthropic,
                        messages=anthropic_messages,
                        params=params,
                        mcp_manager=mcp_manager,
                        enabled_tools=enabled_tools,
                        multimodal=multimodal
                    ),
                    media_type="text/event-stream"
                )
            except Exception as e:
                log_error(f"Anthropic API error (stream): {e}", {"model": model, "stream": True})
                raise e
        else:
            try:
                return StreamingResponse(
                    anthropic_non_stream_generator(
                        response=response,
                        anthropic_client=anthropic,
                        params=params,
                        messages=anthropic_messages,
                        mcp_manager=mcp_manager,
                        enabled_tools=enabled_tools,
                        multimodal=multimodal
                    ),
                    media_type="text/event-stream"
                )
            except Exception as e:
                log_error(f"Anthropic API error (non-stream): {e}", {"model": model, "stream": False})
                raise e

    async def handle_gemini(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str,
        mcp_manager: PolyMCPClient, # MCP Managerを追加
        enabled_tools: Optional[List[CanonicalToolDefinition]] = None, # MCPツール定義を追加
        toolUse: bool = False,
        reasoning_effort: Optional[str] = None,
        is_reasoning_supported: bool = False,
        reasoning_parameter_type: Optional[str] = None,
        budget_tokens: Optional[int] = None,
        multimodal: bool = False,
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
            "safety_settings": safety_settings,
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": max_tokens,
            "response_mime_type": "text/plain"
        }

        if is_reasoning_supported:
            if reasoning_parameter_type == "budget" and budget_tokens is not None:
                completion_args["thinking_config"] = ThinkingConfig(
                    thinking_budget=budget_tokens,
                    # include_thoughts=True
                )

        if image_generation:
            completion_args["response_modalities"] = [
                "IMAGE",
                "TEXT"
            ]
        else:
            completion_args["system_instruction"] = system
            completion_args["response_modalities"] = [
                "TEXT"
            ]

        if toolUse and enabled_tools:
            tool_config = ToolConfig(
                function_calling_config=FunctionCallingConfig(mode='ANY')
            )
            automatic_function_calling = AutomaticFunctionCallingConfig(
                disable=True,
                ignore_call_history=True
            )
            completion_args["tools"] = [get_gemini_tool_definitions(canonical_tools=enabled_tools)]
            completion_args["tool_config"] = tool_config
            completion_args["automatic_function_calling"] = automatic_function_calling
        elif toolUse:
            log_warning("Tool use requested, but no MCP tools are available/enabled.")

        generation_config = GenerateContentConfig(**completion_args)

        # Process history and current message
        history: list[Content] = []
        images = []
        for message in messages[:-1]:
            parts = []
            role = "model" if message["role"] == "assistant" else message["role"]
            for content in message["content"]:
                if content["type"] == "image":
                    # Base64エンコードされた文字列を取得
                    base64_data_string = content["source"]["data"]
                    decoded_data = base64.b64decode(base64_data_string)
                    mime_type = content["source"]["media_type"]
                    
                    # sizeが20MB未満かどうか判定
                    if len(decoded_data) > 20 * 1024 * 1024:
                        log_info("Uploading image via Files API")
                        uploaded_image = await upload_image_to_gemini(
                            decoded_data,
                            mime_type
                        )
                        parts.append(
                            Part.from_uri(
                                file_uri=uploaded_image.uri, 
                                mime_type=uploaded_image.mime_type
                            )
                        )
                        images.append(uploaded_image)
                    else:
                        parts.append(
                            Part.from_bytes(
                                data=decoded_data,
                                mime_type=mime_type
                            )
                        )

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
                # Base64エンコードされた文字列を取得
                base64_data_string = content["source"]["data"]
                decoded_data = base64.b64decode(base64_data_string)
                mime_type = content["source"]["media_type"]
                
                # sizeが20MB未満かどうか判定
                if len(decoded_data) > 20 * 1024 * 1024:
                    uploaded_image = await upload_image_to_gemini(
                        decoded_data,
                        mime_type
                    )
                    latest_parts.append(
                        Part.from_uri(
                            file_uri=uploaded_image.uri, 
                            mime_type=uploaded_image.mime_type
                        )
                    )
                    images.append(uploaded_image)
                else:
                    latest_parts.append(
                        Part.from_bytes(
                            data=decoded_data,
                            mime_type=mime_type
                        )
                    )

        latest_content = Content(parts=latest_parts, role="user")

        # Add latest content to history
        history.append(latest_content)
        

        if stream:
            try:
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
                        images=images,
                        mcp_manager=mcp_manager,
                        enabled_tools=enabled_tools,
                        multimodal=multimodal
                    ),
                    media_type="text/event-stream"
                )
            except Exception as e:
                log_error(f"Gemini API error (stream): {e}", {"model": model, "stream": True})
                raise e
        else:
            try:
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
                        completion_args=completion_args,
                        images=images,
                        mcp_manager=mcp_manager,
                        enabled_tools=enabled_tools,
                        multimodal=multimodal
                    ),
                    media_type="text/event-stream"
                )
            except Exception as e:
                log_error(f"Gemini API error (non-stream): {e}", {"model": model, "stream": False})
                raise e
        
    async def handle_xai(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str,
        mcp_manager: PolyMCPClient, # MCP Managerを追加
        enabled_tools: Optional[List[CanonicalToolDefinition]] = None, # MCPツール定義を追加
        toolUse: bool = False,
        reasoning_effort: Optional[str] = None,
        is_reasoning_supported: bool = False,
        reasoning_parameter_type: Optional[str] = None,
        budget_tokens: Optional[int] = None,
        multimodal: bool = False,
        image_generation: bool = False
    ) -> Any:
        """Handle XAI API requests with optional function calling.
        
        If a BadRequest error indicates that stream mode is unsupported,
        the generation falls back to non-streaming mode using common logic.
        """
        xai = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )
        xai_messages = await prepare_openai_messages(system, messages)

        completion_args = {
            "model": model,
            "messages": xai_messages,
            "max_completion_tokens": max_tokens,
            "stream": stream,
            "temperature": temperature
        }

        if is_reasoning_supported:
            if reasoning_parameter_type == "effort" and reasoning_effort:
                completion_args["reasoning_effort"] = reasoning_effort
            # elif reasoning_parameter_type == "budget" and budget_tokens:
            #     completion_args["budget_tokens"] = budget_tokens

        if toolUse and enabled_tools:
            completion_args["tools"] = get_tool_definitions(canonical_tools=enabled_tools)
            completion_args["tool_choice"] = "required"
        elif toolUse:
            log_warning("Tool use requested, but no MCP tools are available/enabled.")

        # If streaming is requested, try using stream mode.
        if stream:
            completion_args["stream_options"] = { "include_usage": True }
            try:
                response = await xai.chat.completions.create(**completion_args)
                return StreamingResponse(
                    openai_stream_generator(
                        response,
                        openai_client=xai,
                        openai_messages=xai_messages,
                        completion_args=completion_args,
                        mcp_manager=mcp_manager,
                        enabled_tools=enabled_tools,
                        multimodal=multimodal
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
                            openai_client=xai, 
                            completion_args=completion_args, 
                            openai_messages=xai_messages,
                            mcp_manager=mcp_manager,
                            enabled_tools=enabled_tools,
                            multimodal=multimodal
                        ),
                        media_type="text/event-stream"
                    )
                else:
                    log_error(f"XAI API error (stream): {e}", {"model": model, "stream": True})
                    raise e
        else:
            completion_args["stream"] = False
            try:
                # For explicit non-stream requests, delegate to the common function.
                return StreamingResponse(
                    openai_non_stream_generator(
                        openai_client=xai, 
                        completion_args=completion_args, 
                        openai_messages=xai_messages,
                        mcp_manager=mcp_manager,
                        enabled_tools=enabled_tools,
                        multimodal=multimodal
                    ),
                    media_type="text/event-stream"
                )
            except Exception as e:
                log_error(f"XAI API error (non-stream): {e}", {"model": model, "stream": False})
                raise e

    async def handle_openrouter(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        stream: bool,
        system: str,
        mcp_manager: PolyMCPClient, # MCP Managerを追加
        enabled_tools: Optional[List[CanonicalToolDefinition]] = None, # MCPツール定義を追加
        toolUse: bool = False,
        reasoning_effort: Optional[str] = None,
        is_reasoning_supported: bool = False,
        reasoning_parameter_type: Optional[str] = None,
        budget_tokens: Optional[int] = None,
        multimodal: bool = False,
        image_generation: bool = False
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

        if toolUse and enabled_tools:
            completion_args["tools"] = get_tool_definitions(canonical_tools=enabled_tools)
            completion_args["tool_choice"] = "required"
        elif toolUse:
            log_warning("Tool use requested, but no MCP tools are available/enabled.")

        response = await openrouter.chat.completions.create(**completion_args)

        if stream:
            completion_args["stream_options"] = {"include_usage": True}
            try:
                return StreamingResponse(
                    openai_stream_generator(
                        response,
                        openai_client=openrouter,
                        openai_messages=openrouter_messages,
                        completion_args=completion_args,
                        mcp_manager=mcp_manager,
                        enabled_tools=enabled_tools,
                        multimodal=multimodal
                    ),
                    media_type="text/event-stream"
                )
            except Exception as e:
                log_error(f"OpenRouter API error (stream): {e}", {"model": model, "stream": True})
                raise e
        else:
            try:
                return StreamingResponse(
                    openai_non_stream_generator(
                        openai_client=openrouter,
                        completion_args=completion_args,
                        openai_messages=openrouter_messages,
                        mcp_manager=mcp_manager,
                        enabled_tools=enabled_tools,
                        multimodal=multimodal
                    ),
                    media_type="text/event-stream"
                ) 
            except Exception as e:
                log_error(f"OpenRouter API error (non-stream): {e}", {"model": model, "stream": False})
                raise e

    async def handle_chat_request(
            self, 
            chat_request: ChatRequest, 
            vendor: str,
            mcp_manager: PolyMCPClient
    ) -> Any:
        """
        Main entry point for handling chat requests.
        Retrieves MCP tools if toolUse is enabled.

        Args:
            chat_request: ChatRequest object containing all request parameters
            vendor: The vendor name (e.g., 'openai', 'anthropic')
            api_key: The decrypted API key for the specified vendor
            mcp_manager: The PolyMCPClient instance

        Returns:
            Appropriate response based on the model and streaming settings
        """
        try:
            messages = await prepare_api_messages(chat_request.messages, multimodal=chat_request.multimodal)

            all_canonical_tools: List[CanonicalToolDefinition] = [] # 全てのツール (built-in + MCP)
            filtered_canonical_tools: Optional[List[CanonicalToolDefinition]] = None # フィルタリング後の有効なツール
            system = chat_request.system # デフォルトのシステムプロンプト


            if chat_request.toolUse:
                log_info("ToolUse enabled, fetching and filtering available tools...")
                try:
                    # 1. Built-in ツールを取得
                    builtin_tool_funcs = get_builtin_tool_functions()
                    builtin_canonical_tools = [generate_builtin_tool_definition(func) for func in builtin_tool_funcs]
                    log_info(f"Fetched {len(builtin_canonical_tools)} built-in tools.")
                    all_canonical_tools.extend(builtin_canonical_tools)

                    # 2. MCP ツールを取得 (Canonical形式)
                    mcp_canonical_tools = await mcp_manager.get_available_tools(vendor="canonical")
                    log_info(f"Fetched {len(mcp_canonical_tools)} total MCP tools.")
                    all_canonical_tools.extend(mcp_canonical_tools)

                    log_info(f"Total available tools (built-in + MCP): {len(all_canonical_tools)}")

                    # 3. DBから無効なツールリストを取得
                    disabled_tools = self.settings_service.get_disabled_mcp_tools(TEMP_USER_ID)
                    disabled_tools_set = set(disabled_tools) # 高速なルックアップのためセットに変換
                    log_info(f"Disabled tools from settings: {disabled_tools}")

                    # 4. 無効なツールを除外してフィルタリング
                    if all_canonical_tools:
                        # CanonicalToolDefinition は TypedDict なので辞書としてアクセス
                        filtered_canonical_tools = [
                            tool for tool in all_canonical_tools
                            if tool["name"] not in disabled_tools_set
                        ]
                        log_info(f"Enabled tools after filtering: {len(filtered_canonical_tools)}")
                        # 有効なツールの名前リストもログに出力（デバッグ用）
                        enabled_tool_names = [t['name'] for t in filtered_canonical_tools]
                        log_info(f"Enabled tool names: {enabled_tool_names}")
                    else:
                        filtered_canonical_tools = []
                        log_info("No tools available (built-in or MCP).")

                    # 5. ツールを使う場合のシステムプロンプトを追加
                    if filtered_canonical_tools: # 有効なツールがある場合のみ指示を追加
                        system = f"{chat_request.system}\n\n{TOOL_USE_INSTRUCTION}"
                    else:
                        log_warning("Tool use requested, but no tools are available/enabled after filtering.")
                        # ツールがない場合は TOOL_USE_INSTRUCTION を追加しない
                        system = chat_request.system

                except Exception as e:
                    log_error(f"Error fetching or filtering tools: {e}")
                    # ツール取得/フィルタリングエラーの場合、ツールなしで続行
                    filtered_canonical_tools = None
                    system = chat_request.system # エラー時は通常のシステムプロンプト

            else:
                # toolUse が False の場合はツールを取得しない
                filtered_canonical_tools = None
                system = chat_request.system
            
            handler = self.handlers.get(vendor)

            if not handler:
                raise HTTPException(status_code=400, detail=f"Unsupported vendor: {vendor}")

            return await handler(
                model=chat_request.model,
                messages=messages,
                max_tokens=chat_request.maxTokens,
                temperature=chat_request.temperature,
                stream=chat_request.stream,
                system=system,
                toolUse=chat_request.toolUse,
                reasoning_effort=chat_request.reasoningEffort,
                is_reasoning_supported=chat_request.isReasoningSupported,
                reasoning_parameter_type=chat_request.reasoningParameterType,
                budget_tokens=chat_request.budgetTokens,
                multimodal=chat_request.multimodal,
                image_generation=chat_request.imageGeneration,
                mcp_manager=mcp_manager, # MCP Manager を渡す
                enabled_tools=filtered_canonical_tools   # MCP ツール定義を渡す
            )

        except Exception as e:
            # handle_chat_requestレベルでのエラー捕捉
            log_error(f"Error in handle_chat_request: {e}", {"vendor": vendor, "model": chat_request.model})
            # isinstanceでHTTPExceptionをチェックし、それ以外は500エラーにする
            if isinstance(e, HTTPException):
                raise e
            else:
                raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")