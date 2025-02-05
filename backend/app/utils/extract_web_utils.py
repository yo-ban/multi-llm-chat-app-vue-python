import base64
import os
import tempfile
from typing import Dict, Tuple, Optional, Any
from app.utils.logging_utils import get_logger, log_error, log_info, log_warning, log_debug

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

        # # save images
        # with open("screenshot.png", "wb") as f:
        #     f.write(screenshot_bytes)
        await browser.close()
        return text, screenshot_base64

def extract_relevant_info(text: str, screenshot_base64: str, query: str) -> str:
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

    # Import necessary modules and configure the Gemini API.

    import google.generativeai as genai
    from dotenv import load_dotenv
    load_dotenv()

    # Configure the Gemini API using the key from environment variables.
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    # Write the Base64 screenshot data to a temporary file.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
        temp_file.write(base64.b64decode(screenshot_base64))
        temp_file_path = temp_file.name

    # Upload the temporary image file to Gemini.
    try:
        uploaded_file = genai.upload_file(temp_file_path, mime_type="image/png")
    except Exception as upload_error:
        os.remove(temp_file_path)
        raise upload_error

    # Remove the temporary file after uploading.
    os.remove(temp_file_path)

    # Generation configuration for Gemini 2.0 Flash.
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]

    # Create the GenerativeModel with the designated system instruction.
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
        system_instruction=BROWSING_SYSTEM_PROMPT,
    )

    # Start a chat session including both the uploaded screenshot and the text prompt.
    chat_session = model.start_chat()

    # Send an empty message to trigger response generation.
    response = chat_session.send_message([uploaded_file.uri, BROWSING_USER_PROMPT], safety_settings=safety_settings)

    # Return the generated text from the AI model.
    return response.text

async def extract_web_site(url: str, query: str) -> Dict[str, Any]:
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
        Exception: Any exceptions during webpage access or information extraction are caught
                  and returned in the response dictionary
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
        relevant_info = extract_relevant_info(text, screenshot_base64, query)
        
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
