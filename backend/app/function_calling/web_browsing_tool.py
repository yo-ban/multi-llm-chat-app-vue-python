import base64
import os
from typing import Dict, Tuple, Any
from app.utils.logging_utils import get_logger, log_error, log_info, log_warning, log_debug
from io import BytesIO
from google import genai
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
from app.utils.stream_generators import parse_usage_gemini

async def retrieve_page_data(url: str) -> Tuple[str, str]:
    """
    指定した URL にアクセスしてページ全体のテキストとスクリーンショット（Base64形式）を取得する関数

    Args:
        url (str): スクレイピング対象のURL

    Returns:
        Tuple[str, str]: (ページテキスト, スクリーンショットのBase64エンコード文字列)
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        # ページテキストを取得
        text = await page.evaluate("() => document.body.innerText")
        # ページ全体のスクリーンショットを取得し、Base64エンコード
        screenshot_bytes = await page.screenshot(full_page=True)
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')

        await browser.close()
        return text, screenshot_base64

async def extract_relevant_info(text: str, screenshot_base64: str, query: str) -> str:
    """
    Gemini 2.0 Flash（Google Gen AI SDK経由）に対して、取得したページテキストとスクリーンショットの情報
    を元に、クエリに関連する部分のみを抽出して返す関数

    Args:
        text (str): Webページから抽出したテキスト
        screenshot_base64 (str): スクリーンショットのBase64エンコードデータ
        query (str): 抽出したい情報に関するクエリ

    Returns:
        str: クエリに関連する抽出情報
    """
    # System prompt as per Gemini API requirements.
    BROWSING_SYSTEM_PROMPT = r"""Review the information on the given website and return information relevant to the query.
Images and text are information from the same website. Text is mechanically extracted and of low quality.
Images should be read visually.

Present the website's content inside a Markdown code block. 
Include both the directly relevant information and enough surrounding context to ensure the material is understood. 
Only output the site's content—do not add any additional explanations. 
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

    # User prompt includes the page text and query.
    BROWSING_USER_PROMPT = f"""
Page text:
```
{text}
```

Query: {query}
"""

    from dotenv import load_dotenv
    load_dotenv()

    # Configure the Gemini API using the key from environment variables.
    client = genai.Client(
        api_key=os.getenv('GEMINI_API_KEY'),
        http_options={'api_version': 'v1alpha'}
    )
    
    # Create BytesIO object for the image
    image_bytes = base64.b64decode(screenshot_base64)    
    image_buffer = BytesIO(image_bytes)
    # Upload the temporary image file to Gemini.
    try:
        uploaded_file: File = client.files.upload(file=image_buffer, config={"mime_type": "image/png"})
    except Exception as upload_error:
        raise upload_error

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

    content = Content(
        parts=[
            Part.from_text(text=BROWSING_USER_PROMPT),
            Part.from_uri(file_uri=uploaded_file.uri, mime_type="image/png")
        ],
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

    response = await chat.send_message_stream(content)

    text = ""
    try:
        async for event in response:
            text += event.text
        if event.usage_metadata:
            usage = await parse_usage_gemini(event.usage_metadata)
            log_info("Token usage in web extraction", usage)
    except Exception as e:
        raise e

    try:
        client.files.delete(name=uploaded_file.name)
    except Exception as e:
        log_warning(f"Image delete failed: {e}")

    return text

async def web_browsing(url: str, query: str) -> Dict[str, Any]:
    """
    Extract information from a specified webpage based on a query using Playwright for scraping
    and Gemini 2.0 Flash for information extraction.

    This function performs the following steps:
    1. Retrieves the webpage content and takes a screenshot using Playwright
    2. Uses Gemini 2.0 Flash to analyze the content and extract relevant information
    3. Returns the extracted information along with metadata

    Args:
        url (str): The URL of the webpage to extract information from
        query (str): The query specifying what information to extract from the webpage

    Returns:
        Dict[str, Any]: A dictionary containing:
            - url: The target URL
            - query: The search query
            - extracted_info: The extracted relevant information
            - error: Error message if an error occurred (optional)
            - status: Status of the extraction ("success" or "error")
            - timestamp: ISO format timestamp of when the extraction was performed

    Raises:
        Exception: Any exceptions during webpage access or information extraction are caught and returned in the response dictionary
    """
    from datetime import datetime, timezone
    import traceback

    response = {
        "url": url,
        "query": query,
        "status": "error",  # Default to error, will be updated on success
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    try:
        # Retrieve page data
        log_debug("Retrieving page data", {"url": url})
        text, screenshot_base64 = await retrieve_page_data(url)
        
        # Extract relevant information using Gemini
        log_debug("Extracting relevant information using Gemini", {"query": query})
        relevant_info = await extract_relevant_info(text, screenshot_base64, query)
        
        # Update response with success data
        response.update({
            "status": "success",
            "extracted_info": relevant_info
        })
        
        log_info("Successfully extracted web information", {
            "url": url,
            "query": query,
            "info_length": len(relevant_info) if relevant_info else 0
        })
        
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        log_error(f"Error during web extraction: {error_msg}", {
            "url": url,
            "query": query,
            "stack_trace": stack_trace
        })
        
        response.update({
            "error": error_msg,
            "stack_trace": stack_trace if os.getenv("DEBUG", "false").lower() == "true" else None
        })
    
    return response
