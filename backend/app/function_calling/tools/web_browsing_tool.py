import asyncio
import os
import random
import mimetypes
from pydantic import BaseModel
from typing import Dict, Tuple, Any, List, Optional
from urllib.parse import urlparse
from app.logger.logging_utils import get_logger, log_error, log_info, log_warning, log_debug
from io import BytesIO
import httpx
from google import genai
from google.genai.errors import ServerError
from google.genai.types import (
    GenerateContentConfig, 
    SafetySetting, 
    HarmCategory, 
    HarmBlockThreshold, 
    Content,
    File,
    Part
)
from app.message_utils.usage_parser import parse_usage_gemini

class WebExtractionResult(BaseModel):
    """
    Represents a web extraction result
    """
    url: str
    query: str
    status: str
    timestamp: str
    content_type: str
    is_web_page: bool
    extracted_info: str | List[str] | None = None
    error: Optional[str] = None
    stack_trace: Optional[str] = None

SKIP_GEMINI_EXTENSIONS = [
    '.ipynb',
    '.py',
    '.txt',
    '.md',
    # '.csv',
] 

# Supported MIME types for Gemini document processing
SUPPORTED_MIME_TYPES = {
    'application/pdf': '.pdf',
    'application/x-javascript': '.js',
    'text/javascript': '.js',
    'application/x-python': '.py',
    'text/x-python': '.py',
    'text/plain': '.txt',
    'text/css': '.css',
    'text/md': '.md',
    'text/csv': '.csv',
    'text/xml': '.xml',
    'text/rtf': '.rtf'
}

# Web-related MIME types that should be processed using Playwright
WEB_MIME_TYPES = {
    'text/html': '.html',
    'application/xhtml+xml': '.html',
    'application/html': '.html'
}

async def format_web_extraction(result: WebExtractionResult) -> str:
    """Format web extraction results into a readable text format."""
    if result.status == "error":
        return f"Error extracting content: {result.error or 'Unknown error'}"
    
    formatted_text = []
    formatted_text.append(f"Extracted from: {result.url}")
    if result.extracted_info:
        formatted_text.append(f"\n{result.extracted_info}")
    if result.error:
        formatted_text.append(f"\n{result.error}")
    return "\n".join(formatted_text)

async def retrieve_page_data(url: str, content_type: Optional[str] = None, is_web_page: Optional[bool] = None) -> Tuple[List[File] | str, bool]:
    """
    指定した URL にアクセスしてコンテンツを取得し、Gemini API用のFileオブジェクトとして返す関数

    Args:
        url (str): 取得対象のURL
        content_type (Optional[str]): 事前に判定されたコンテンツタイプ。Noneの場合は自動判定
        is_web_page (Optional[bool]): 事前に判定されたWebページフラグ。Noneの場合は自動判定

    Returns:
        List[File]: Gemini APIにアップロード済みのFileオブジェクトのリスト
        - 通常のWebページの場合: [スクリーンショットのFile, テキストのFile]
        - PDF等のドキュメントの場合: [ドキュメントのFile]
    """

    from playwright.async_api import async_playwright
    from playwright_stealth import stealth_async
    from markdownify import markdownify as md
    from dotenv import load_dotenv
    load_dotenv()

    client = genai.Client(
        api_key=os.getenv('GEMINI_API_KEY'),
        http_options={'api_version': 'v1alpha'}
    )

    parsed_url = urlparse(url)
    path = parsed_url.path.split('.')[-1]

    # ファイルの直接リンクの場合
    if not is_web_page and path in SKIP_GEMINI_EXTENSIONS:

        # ファイルをダウンロード
        response = httpx.get(url)
        response.raise_for_status()
        file_data = BytesIO(response.content)

        # ファイルをテキストに変換
        file_data = file_data.getvalue().decode('utf-8')
        
        return file_data, False

    # ドキュメントファイルの場合（PDF等）
    if not is_web_page and content_type in SUPPORTED_MIME_TYPES:
        try:
            # ファイルをダウンロード
            response = httpx.get(url)
            response.raise_for_status()
            file_data = BytesIO(response.content)
            
            # Gemini APIにアップロード
            uploaded_file = client.files.upload(
                file=file_data,
                config={"mime_type": content_type}
            )
            return [uploaded_file], True
            
        except Exception as e:
            log_error(f"Error downloading or uploading document: {str(e)}")
            raise e

    # 通常のWebページの場合
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # await stealth_async(page)
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        })
        success_playwright = False
        try:
            # First attempt with networkidle strategy but with a shorter timeout
            await page.goto(url, wait_until="networkidle", timeout=10000)
            success_playwright = True

        except Exception as e:
            log_warning(f"Initial navigation with networkidle timed out, trying alternative approach: {str(e)}")
            
            try:
                # Alternative approach: navigate without waiting, then use waitForFunction
                await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                success_playwright = True

            except Exception as e:

                try:
                    # Wait for DOM to be ready and URL to be loaded
                    await page.wait_for_function("""
                        () => {
                            const readyStateCondition = document.readyState === 'interactive' || document.readyState === 'complete';
                            return readyStateCondition;
                        }
                    """, timeout=10000)
                    success_playwright = True

                except Exception as e:
                    log_error(f"Error during navigation: {str(e)}")
                    success_playwright = False

        # Add a random delay of 500 to 2000 milliseconds to simulate human behavior
        await asyncio.sleep(random.randint(500, 2000) / 1000)

        # Scroll the page to load additional content
        await page.evaluate("() => window.scrollBy(0, window.innerHeight)")

        # ページテキストを取得
        # text = await page.evaluate("() => document.body.innerText")
        page_html = await page.content()

        # スクリーンショットを取得
        screenshot_bytes = await page.screenshot(full_page=True)
        screenshot_buffer = BytesIO(screenshot_bytes)

        await browser.close()

        try:
            if success_playwright:
                text = md(page_html)
                text_buffer = BytesIO(text.encode('utf-8'))

                # テキストとスクリーンショットをGemini APIにアップロード
                text_file = client.files.upload(
                    file=text_buffer,
                    config={"mime_type": "text/plain"}
                )
                screenshot_file = client.files.upload(
                    file=screenshot_buffer,
                    config={"mime_type": "image/png"}
                )
                return [screenshot_file, text_file], True
            
            else:
                response = httpx.get("https://r.jina.ai/" + url)
                response.raise_for_status()
                text = md(response.text)
                text_buffer = BytesIO(text.encode('utf-8'))
                # テキストとスクリーンショットをGemini APIにアップロード
                text_file = client.files.upload(
                    file=text_buffer,
                    config={"mime_type": "text/plain"}
                )
                return [text_file], True
            
        except Exception as e:
            log_error(f"Error uploading files to Gemini: {str(e)}")
            raise e

async def extract_relevant_info(files: List[File], query: str) -> str:
    """
    Gemini 2.0 Flash（Google Gen AI SDK経由）に対して、アップロード済みのファイルを元に、
    クエリに関連する部分のみを抽出して返す関数

    Args:
        files (List[File]): Gemini APIにアップロード済みのFileオブジェクトのリスト
        query (str): 抽出したい情報に関するクエリ

    Returns:
        str: クエリに関連する抽出情報
    """

    # System prompt as per Gemini API requirements.
    BROWSING_SYSTEM_PROMPT = r"""Review the information from the provided content and return information relevant to the query.
For web pages, images and text are information from the same website. Text is mechanically extracted and of low quality.
Images should be read visually.

For documents (PDF, etc.), analyze both the text content and any visual elements like diagrams, charts, and tables.

Present the each section of content inside a Markdown code block. 
Include both the directly relevant information and enough surrounding context to ensure the material is fully understood. 
Only output the content—do not add any additional explanations. 
Format any figures or tables using Markdown-friendly structures, and ensure that code within code blocks is escaped properly with backticks (for example, \`\`\` for multi-line code).

If the content is organized into separated sections and some sections are less essential, you may omit those and return multiple segments. 
When returning multiple segments, use the following format for each section:

Output format:

**Section 1:**
```
...
...
[Content for Section 1]

\`\`\`
code block in code block will be escaped with backticks (e.g., \`\`\`).
\`\`\`

...
...
```

**Section 2:**
```
...
...
[Content for Section 2]

\`\`\`
code block in code block will be escaped with backticks (e.g., \`\`\`).
\`\`\`

...

...
```

...and so on.
"""

    from dotenv import load_dotenv
    load_dotenv()

    # Configure the Gemini API using the key from environment variables.
    client = genai.Client(
        api_key=os.getenv('GEMINI_API_KEY'),
        http_options={'api_version': 'v1alpha'}
    )

    safety_settings = [
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
            threshold=HarmBlockThreshold.BLOCK_NONE
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=HarmBlockThreshold.BLOCK_NONE
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=HarmBlockThreshold.BLOCK_NONE
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=HarmBlockThreshold.BLOCK_NONE
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=HarmBlockThreshold.BLOCK_NONE
        )
    ]

    # Create content parts from files
    parts = [Part.from_text(text=f"Query: {query}")]
    for file in files:
        parts.append(Part.from_uri(file_uri=file.uri, mime_type=file.mime_type))

    content = Content(
        parts=parts,
        role="user"
    )

    # Generation configuration for Gemini 2.0 Flash.
    generation_config = GenerateContentConfig(
        response_modalities=["TEXT"],
        safety_settings=safety_settings,
        system_instruction=BROWSING_SYSTEM_PROMPT,
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="text/plain",
    )

    chat = client.aio.chats.create(
        history=[],
        model=os.getenv("GEMINI_MODEL_NAME"),
        config=generation_config
    )

    max_retries = 3
    retries = 0
    while retries < max_retries:
        try:
            response = await chat.send_message_stream(content)

            text = ""
            async for event in response:
                text += event.text

            if event.usage_metadata:
                usage = await parse_usage_gemini(event.usage_metadata)
                log_info("Token usage in web extraction", usage)

            break
        except Exception as e:
            log_error(f"Error sending message to Gemini: {e}")
            if isinstance(e, ServerError) and e.code == 503 and 'The model is overloaded' in e.message:
                retries += 1
                if retries == max_retries:
                    raise e
                await asyncio.sleep(1)
            else:
                raise e

    # Clean up uploaded files
    for file in files:
        try:
            client.files.delete(name=file.name)
        except Exception as e:
            log_warning(f"File delete failed: {e}")

    if text.startswith("```\n**Section"):
        text = text[3:]

    # Return the generated text from the AI model.
    return text

async def detect_mime_type(url: str) -> Tuple[str, bool]:
    """
    URLからコンテンツをダウンロードし、実際のファイル内容からMIMEタイプを判定する関数

    Args:
        url (str): 判定対象のURL

    Returns:
        Tuple[str, bool]: (MIMEタイプ, Webページかどうかのフラグ)
    """
    try:
        import magic

        # ヘッダーのみを取得してContent-Typeをチェック
        async with httpx.AsyncClient() as client:
            response = await client.head(url, follow_redirects=True)
            header_content_type = response.headers.get('content-type', '').split(';')[0].lower()

            # ヘッダーのContent-Typeが明確なWebページ系の場合は、それを信頼
            if header_content_type in WEB_MIME_TYPES:
                return header_content_type, True

        # コンテンツの先頭部分のみをダウンロード（最大32KB）
        async with httpx.AsyncClient() as client:
            async with client.stream('GET', url) as response:
                content = b''
                async for chunk in response.aiter_bytes():
                    content += chunk
                    if len(content) >= 32768:  # 32KB
                        break

        # python-magicを使用してバイナリコンテンツからMIMEタイプを判定
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_buffer(content)

        # パスからの判定も併用
        parsed_url = urlparse(url)
        path = parsed_url.path
        path_mime = mimetypes.guess_type(path)[0]

        # MIMEタイプの判定ロジック
        final_mime = detected_mime or path_mime or 'application/octet-stream'
        
        # Webページかどうかの判定
        is_web_page = (
            final_mime in WEB_MIME_TYPES or
            path.endswith('/') or
            not path or
            '.' not in path.split('/')[-1]
        )

        return final_mime, is_web_page

    except Exception as e:
        log_warning(f"Error during MIME type detection: {str(e)}")
        # エラーの場合はパスベースの判定にフォールバック
        parsed_url = urlparse(url)
        path = parsed_url.path
        mime_type = mimetypes.guess_type(path)[0] or 'text/html'
        is_web_page = (
            mime_type in WEB_MIME_TYPES or
            path.endswith('/') or
            not path or
            '.' not in path.split('/')[-1]
        )
        return mime_type, is_web_page

async def web_browsing(url: str, query: str) -> str:
    """
    Perform an interactive web browsing session on a given URL to investigate its content in detail.

    Args:
        url: The URL of the webpage to extract information from. Must be a valid HTTP/HTTPS URL.
        query: Specific details you want to extract from the webpage.

    Returns:
        str: A string containing the extracted information

    Raises:
        Exception: Any exceptions during content retrieval or information extraction are caught and returned in the response dictionary
    """
    from datetime import datetime, timezone
    import traceback

    # Get content type and web page flag from actual content
    content_type, is_web_page = await detect_mime_type(url)

    log_debug("Content type and web page flag", {
        "content_type": content_type,
        "is_web_page": is_web_page
    })

    response = WebExtractionResult(
        url=url,
        query=query,
        status="error",  # Default to error, will be updated on success
        timestamp=datetime.now(timezone.utc).isoformat(),
        content_type=content_type,
        is_web_page=is_web_page
    )

    try:
        # Retrieve content and upload to Gemini
        log_debug("Retrieving content", {
            "url": url, 
            "content_type": response.content_type,
            "is_web_page": response.is_web_page
        })
        file_data, use_gemini = await retrieve_page_data(url, response.content_type, response.is_web_page)
        
        if use_gemini:
            # Extract relevant information using Gemini
            log_debug("Extracting relevant information using Gemini", {"query": response.query})
            relevant_info = await extract_relevant_info(file_data, response.query)
        else:
            relevant_info = file_data

        # Update response with success data
        response.status = "success"
        response.extracted_info = relevant_info
        
        log_info("Successfully extracted information", {
            "url": response.url,
            "query": response.query,
            "content_type": response.content_type,
            "is_web_page": response.is_web_page,
            "info_length": len(relevant_info) if relevant_info else 0
        })
        
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        log_error(f"Error during extraction: {error_msg}", {
            "url": response.url,
            "query": response.query,
            "content_type": response.content_type,
            "is_web_page": response.is_web_page,
            "stack_trace": stack_trace
        })
        
        response.error = error_msg
        response.stack_trace = stack_trace if os.getenv("DEBUG", "false").lower() == "true" else None
    
    formatted_result = await format_web_extraction(response)
    return formatted_result
