import base64
import asyncio
import os
import mimetypes
from typing import Dict, Tuple, Any, List, Optional
from urllib.parse import urlparse
from app.utils.logging_utils import get_logger, log_error, log_info, log_warning, log_debug
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
from app.utils.logging_utils import log_info
from app.utils.message_utils import parse_usage_gemini

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

async def retrieve_page_data(url: str, content_type: Optional[str] = None, is_web_page: Optional[bool] = None) -> List[File]:
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
    from dotenv import load_dotenv
    load_dotenv()

    client = genai.Client(
        api_key=os.getenv('GEMINI_API_KEY'),
        http_options={'api_version': 'v1alpha'}
    )

    # コンテンツタイプが渡されていない場合は判定
    if content_type is None or is_web_page is None:
        parsed_url = urlparse(url)
        path = parsed_url.path
        detected_type = mimetypes.guess_type(path)[0]
        content_type = content_type or detected_type
        
        # Webページ判定
        is_web_page = is_web_page if is_web_page is not None else (
            detected_type is None or  # MIMEタイプが不明
            detected_type in WEB_MIME_TYPES or  # 明示的なWebページ
            path.endswith('/') or  # ディレクトリURL
            not path or  # パスなし
            '.' not in path.split('/')[-1]  # 拡張子なし
        )
    
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
            return [uploaded_file]
            
        except Exception as e:
            log_error(f"Error downloading or uploading document: {str(e)}")
            raise e

    # 通常のWebページの場合
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        
        # ページテキストを取得
        text = await page.evaluate("() => document.body.innerText")
        text_buffer = BytesIO(text.encode('utf-8'))
        
        # スクリーンショットを取得
        screenshot_bytes = await page.screenshot(full_page=True)
        screenshot_buffer = BytesIO(screenshot_bytes)
        
        await browser.close()

        try:
            # テキストとスクリーンショットをGemini APIにアップロード
            text_file = client.files.upload(
                file=text_buffer,
                config={"mime_type": "text/plain"}
            )
            screenshot_file = client.files.upload(
                file=screenshot_buffer,
                config={"mime_type": "image/png"}
            )
            return [screenshot_file, text_file]
            
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

Present the content inside a Markdown code block. 
Include both the directly relevant information and enough surrounding context to ensure the material is understood. 
Only output the content—do not add any additional explanations. 
Format any figures or tables using Markdown-friendly structures, and ensure that code within code blocks is escaped properly with backticks (for example, \`\`\` for multi-line code).

Output format:
```
...
...
[write website's contents]

\`\`\`
code block in code block will be escaped with backticks (e.g., \`\`\`).
\`\`\`

...
...
```

If the content is organized into separated sections and some sections are less essential, you may omit those and return multiple segments. 
When returning multiple segments, use the following format for each section:

**Section 1:**
```
[Content for Section 1]
```

**Section 2:**
```
[Content for Section 2]
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

    return text

async def web_browsing(url: str, query: str) -> Dict[str, Any]:
    """
    Extract information from a specified URL based on a query using Playwright for web pages
    and direct download for documents, then use Gemini 2.0 Flash for information extraction.

    This function performs the following steps:
    1. Retrieves the content from the URL:
        - For web pages: Uses Playwright to get text and screenshot
        - For documents (PDF, etc.): Downloads and processes directly
    2. Uses Gemini 2.0 Flash to analyze the content and extract relevant information
    3. Returns the extracted information along with metadata

    Args:
        url (str): The URL to extract information from
        query (str): The query specifying what information to extract

    Returns:
        Dict[str, Any]: A dictionary containing:
            - url: The target URL
            - query: The search query
            - extracted_info: The extracted relevant information
            - error: Error message if an error occurred (optional)
            - status: Status of the extraction ("success" or "error")
            - timestamp: ISO format timestamp of when the extraction was performed
            - content_type: The type of content that was processed
            - is_web_page: Whether the content was processed as a web page

    Raises:
        Exception: Any exceptions during content retrieval or information extraction are caught and returned in the response dictionary
    """
    from datetime import datetime, timezone
    import traceback

    # Get content type from URL
    parsed_url = urlparse(url)
    path = parsed_url.path
    content_type = mimetypes.guess_type(path)[0]
    
    # Determine if it's a web page
    is_web_page = (
        content_type is None or  # MIMEタイプが不明
        content_type in WEB_MIME_TYPES or  # 明示的なWebページ
        path.endswith('/') or  # ディレクトリURL
        not path or  # パスなし
        '.' not in path.split('/')[-1]  # 拡張子なし
    )

    response = {
        "url": url,
        "query": query,
        "status": "error",  # Default to error, will be updated on success
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content_type": content_type or "text/html",  # Default to HTML if type cannot be determined
        "is_web_page": is_web_page
    }

    try:
        # Retrieve content and upload to Gemini
        log_debug("Retrieving content", {
            "url": url, 
            "content_type": response["content_type"],
            "is_web_page": is_web_page
        })
        files = await retrieve_page_data(url, content_type, is_web_page)
        
        # Extract relevant information using Gemini
        log_debug("Extracting relevant information using Gemini", {"query": query})
        relevant_info = await extract_relevant_info(files, query)
        
        # Update response with success data
        response.update({
            "status": "success",
            "extracted_info": relevant_info
        })
        
        log_info("Successfully extracted information", {
            "url": url,
            "query": query,
            "content_type": response["content_type"],
            "is_web_page": is_web_page,
            "info_length": len(relevant_info) if relevant_info else 0
        })
        
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        log_error(f"Error during extraction: {error_msg}", {
            "url": url,
            "query": query,
            "content_type": response["content_type"],
            "is_web_page": is_web_page,
            "stack_trace": stack_trace
        })
        
        response.update({
            "error": error_msg,
            "stack_trace": stack_trace if os.getenv("DEBUG", "false").lower() == "true" else None
        })
    
    return response
