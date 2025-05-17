import os
import asyncio
from pydantic import BaseModel
from typing import List, Dict, Any
import aiohttp
from google import genai
from google.genai.types import (
    Tool, 
    GenerateContentConfig, 
    GoogleSearch, 
    GroundingMetadata, 
    SafetySetting, 
    HarmCategory, 
    HarmBlockThreshold
)
from google.genai.errors import ServerError
from app.logger.logging_utils import get_logger, log_error, log_info, log_warning, log_debug
from app.message_utils.usage_parser import parse_usage_gemini
# Get logger instance
logger = get_logger()

class SearchResult(BaseModel):
    """
    Represents a web search result
    """
    title: str
    link: str
    snippet: str 

async def resolve_redirect_url(url: str) -> str:
    """
    Resolve a redirect URL to its final destination
    
    Args:
        url: The redirect URL to resolve
        
    Returns:
        The final destination URL
    """
    if not url.startswith("https://vertexaisearch.cloud.google.com/"):
        return url
        
    try:
        async with aiohttp.ClientSession(max_field_size=8190*2, max_line_size=8190*2, timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url, allow_redirects=True) as response:
                # Get the final URL after all redirects
                final_url = str(response.url)
                return final_url
    except Exception as e:
        log_error(f"Error resolving URL {url}: {str(e)}")
        return url

async def format_search_results(results: List[SearchResult]) -> str:
    """Format web search results into a readable text format."""
    formatted_text = []
    for i, result in enumerate(results, 1):
        formatted_text.append(f"{i}. {result.title}")
        formatted_text.append(f"   {result.link}")
        if result.snippet:
            formatted_text.append(f"   {result.snippet}\n")
    return "\n".join(formatted_text)

async def extract_sources_from_metadata(metadata: GroundingMetadata, num_results: int) -> List[SearchResult]:
    """
    Extract sources from Gemini's grounding metadata
    
    Args:
        metadata: Grounding metadata from Gemini response
        num_results: Maximum number of results to return
        
    Returns:
        List of SearchResult objects
    """
    source_map: Dict[str, SearchResult] = {}
    
    chunks = metadata.grounding_chunks
    supports = metadata.grounding_supports
    
    for index, chunk in enumerate(chunks):
        web_info = chunk.web
        url = web_info.uri
        title = web_info.title
        
        if url and title:
            # Resolve the redirect URL
            resolved_url = await resolve_redirect_url(url)
            
            if resolved_url not in source_map:
                # Find snippets that reference this chunk
                snippets = []
                for support in supports:
                    if index in support.grounding_chunk_indices:
                        segment = support.segment
                        if segment and segment.text:
                            snippets.append(segment.text)
                
                source_map[resolved_url] = SearchResult(
                    title=title,
                    link=resolved_url,
                    snippet=" ".join(snippets) if snippets else ""
                )
    
    results = list(source_map.values())[:num_results]
    return results

async def web_search(query: str, num_results: int = 5) -> str:
    """
    Perform a targeted web search to retrieve relevant URLs along with concise snippets.
    - Purpose: Propose specific suggestions or questions to help the user refine and specify their vague or ambiguous request.
    - Usage Guidelines:
        - Use this tool when the user's request lacks sufficient detail or is open to multiple interpretations.
        - Generate concrete suggestions or clarifying questions based on potential interpretations of the user's request.
        - Aim to guide the user towards providing the necessary specifics for the request to be actionable.
        - Present suggestions/questions clearly and concisely.

    Args:
        query: Specific details you want to search for on the web. One issue per search.
        num_results: Number of results to return (recommended (default): 5)
        
    Returns:
        str: Formatted search results as a string
    """
    try:
        
        from dotenv import load_dotenv
        load_dotenv()

        client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY"),
            http_options={'api_version': 'v1alpha'}
        )
        model_id = os.getenv("GEMINI_MODEL_NAME")

        google_search_tool = Tool(
            google_search=GoogleSearch()
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

        max_retries = 3
        retries = 0
        while retries < max_retries:
            try:
                        # First, get search results
                response = client.models.generate_content(
                    model=model_id,
                    contents=f"Search using the same language as the question below.\n\nQuestion:{query}",
                    config=GenerateContentConfig(
                        tools=[google_search_tool],
                        response_modalities=["TEXT"],
                        safety_settings=safety_settings,
                        max_output_tokens=1024
                    )
                )
                break
            except Exception as e:
                if isinstance(e, ServerError) and e.code == 503 and 'The model is overloaded' in e.message:
                    retries += 1
                    if retries == max_retries:
                        raise e
                    await asyncio.sleep(1)
                else:
                    raise e

        # Extract and process grounding metadata
        metadata = response.candidates[0].grounding_metadata

        if response.usage_metadata:
            usage = await parse_usage_gemini(response.usage_metadata)
            log_info("Token usage in web search", usage)

        if not metadata:
            log_warning("No search results found", {"query": query})
            return []

        log_info("extract_sources_from_metadata")

        results = await extract_sources_from_metadata(metadata, num_results)
        log_info("Successfully searched web", {
            "query": query,
            "info_length": len(results) if results else 0
        })

        formatted_results = await format_search_results(results)
        return formatted_results
        
    except Exception as e:
        log_error(f"Gemini search error: {str(e)}", additional_info={"query": query, "num_results": num_results})
        return [SearchResult(title="Error", link="", snippet="Error occurred while performing web search")]