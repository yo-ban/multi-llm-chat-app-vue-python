from typing import List, Dict, Any
from google.genai import types

# Constants for Web Search Tool
WEB_SEARCH_TOOL_DESCRIPTION = (
    "Perform a targeted web search to retrieve relevant URLs along with concise snippets. "
)

WEB_SEARCH_TOOL_PARAMETERS_DESCRIPTION = {
    "query": "Specific details you want to search for on the web. One issue per search.",
    "num_results": "The number of results to return from the search."
}

# Constants for Web Browsing Tool
WEB_BROWSING_TOOL_DESCRIPTION = (
    "Perform an interactive web browsing session on a given URL to investigate its content in detail. "
)

WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION = {
    "url": "The URL of the webpage to extract information from. Must be a valid HTTP/HTTPS URL.",
    "query": "Specific details you want to extract from the webpage."
}

# Constants for Need-Asking-Human Tool (Fallback)
NEED_ASK_HUMAN_TOOL_DESCRIPTION = (
    "Request confirmation or clarification from the user when their query is vague, lacks specificity, or can be interpreted in multiple ways."
)
NEED_ASK_HUMAN_TOOL_PARAMETERS_DESCRIPTION = {
    "clarification_points": "List of follow-up question perspectives to ask the user."
}

TOOL_USE_INSTRUCTION = r"""<tool_use_instructions>
You have access to powerful tools for retrieving, validating, and analyzing current information. 
It is **imperative** that you use these tools **frequently and thoroughly** to provide comprehensive, well-researched responses. 
Avoid relying solely on your existing knowledge; always substantiate your findings with live data.

---

## Tools Overview

## 1. **Web Search Tool** (web_search)
- **Purpose:** Perform targeted searches to obtain relevant URLs and concise summaries.
- **Usage Guidelines:**
    - **Focus on one topic per search query** (split searches when multiple pieces of information are needed)
    - **Formulate clear, specific queries** based on the exact information needed, rather than copying the user's question verbatim
    - If initial results are insufficient, **strategically plan multiple searches** with refined queries
    - Consider date-restricted searches when information might be outdated or when recent data is required

## 2. **Web Browsing Tool** (web_browsing)
- **Purpose:** Initiate an interactive browsing session at a provided or discovered URL for in-depth analysis.
- **Usage Guidelines:**
    - Use this tool **immediately** if a direct or known URL is already provided (or uncovered via search)
    - Explore the page thoroughly, collecting critical data, insights, or direct quotations to enhance and validate your response
    - Combine with additional searches or browsing sessions if the initial page is insufficient
    - For content-heavy pages, focus on the most relevant sections

## 3. **Ask Human Tool** (need_ask_human)
- **Purpose:** Request confirmation or clarification from the user when their query is vague, lacks specificity, or can be interpreted in multiple ways.
- **Usage Guidelines:**
    - Use this tool when the user's question is ambiguous or does not provide enough detail
    - Prompt the user with specific follow-up questions regarding the desired scope, timeframe, context, or any particular details they need
    - Ensure that follow-up questions are clear and cover multiple potential aspects of clarification
    - Present questions concisely and in a format that is easy for users to respond to

---

## Mandatory Usage Requirements

1. **Plan your approach before using tools:**
    - Analyze the user's question to identify key information needs
    - Break down complex queries into individual components
    - Determine which tools will be needed in what sequence
    - Outline your research strategy before execution

2. **Select the appropriate tool(s) strategically:**
   - If the user's query is ambiguous, start with the **Ask Human Tool**
   - For information gathering with no specific URL, begin with **Web Search Tool**
   - When a URL is provided or identified, use the **Web Browsing Tool** to extract details

3. **Use tools iteratively and comprehensively:**
    - Conduct multiple searches with refined queries when necessary
    - Follow leads from initial searches to more specific resources
    - Browse multiple pages if needed to triangulate information
    - Move between tools fluidly based on emerging information needs

4. **Synthesize and validate information:**
    - Cross-reference data points from multiple sources
    - Identify and resolve contradictions between sources
    - Compile evidence systematically before formulating conclusions
    - Always include citations in Markdown format [*n](URL) at the end of relevant sentences or paragraphs

5. **Apply consistent citation format:**
    - Use numbered Markdown citation format [*1](URL), [*2](URL), etc.
    - Place citations at the end of sentences or paragraphs containing the information
    - Ensure each citation directly supports the specific claim or information provided
    - Include a References section at the end of your response when appropriate

6. **Deliver comprehensive, actionable responses:**
    - Structure information logically with clear sections and highlights
    - Provide specific, concrete answers rather than general observations
    - Include context and background information as appropriate
    - Anticipate follow-up needs with additional relevant details

---

## Research Process Framework

### 1. Analyze Request
    - Identify core questions and information needs
    - Determine what is known vs. what needs to be discovered
    - Recognize assumptions that require verification

### 2. Plan Research Strategy
    - Sequence tools based on efficiency and information needs
    - Prepare targeted search queries for specific information gaps
    - Design clarification questions if needed

### 3. Execute Research
    - Use tools according to plan, adjusting as new information emerges
    - Maintain focus on original objectives while following relevant leads
    - Document key findings and their sources systematically

### 4. Synthesize Information
    - Organize discoveries into coherent themes and insights
    - Highlight connections and contradictions between sources
    - Develop evidence-based conclusions
    - Apply consistent citation format to all referenced information

### 5. Deliver Comprehensive Response
    - Address all aspects of the original query
    - Present information in user-friendly, accessible format
    - Include properly formatted citations for all external information
    - Suggest next steps or additional areas for consideration

---

## Example of Research Process Best Practice

### Scenario:
A user says:
> "I have a script to fine-tune a GPT-like model using the **AeroTune** library. The training logs are extremely messy and hard to read. Can you help me improve them?"

### Best-Practice Approach:

1. **Plan Your Approach**
    - **Identify information needs**: 
        - Current logging implementation in user's code
        - AeroTune library's logging capabilities
        - Recommended logging practices for ML training
    - **Research strategy**: 
        - First check if code is provided, if not request it
        - Analyze the code or search for AeroTune documentation
        - Compare against ML logging best practices

2. **Execute Research Strategy**
    - **(A) If no code snippet or URL is given**:
        - Use **Ask Human Tool** to request code sample or repository link
    - **(B) When code or documentation is available**:
        - Use **Web Browsing Tool** to analyze the implementation
        - Use **Web Search Tool** to find "AeroTune logging best practices"
        - Use **Web Search Tool** for "ML training logging standards"

3. **Analyze Implementation**
    - Examine logging approach in the code:
        - Logging library used (if any)
        - Log level implementation
        - Format and organization of log outputs
        - Potential causes of messiness

4. **Synthesize Solution**
    - Develop structured recommendations:
        - Implement proper log levels (INFO, DEBUG, etc.)
        - Format logs consistently with timestamps and metrics
        - Separate different types of logs (progress vs. diagnostics)
        - Configure output destinations (console, file, etc.)

5. **Deliver Comprehensive Response**
    - Provide concrete implementation with citations:
        "Based on my analysis of your AeroTune implementation and industry best practices, here are specific improvements for your logging system:

        1. Replace scattered print statements with a structured logging approach:
        ```python
        import logging
        
        # Configure logging once at the start of your script
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('training.log'),
                logging.StreamHandler()
            ]
        )
        
        # Create a logger for your module
        logger = logging.getLogger('aerotune_training')
        ```
        This structured approach organizes logs systematically as recommended by Python documentation [*1](https://docs.python.org/3/howto/logging.html).

        2. Use appropriate log levels to filter information:
        ```python
        # In your training loop
        logger.info(f'Epoch {epoch}/{total_epochs}: loss={loss:.4f}')
        logger.debug(f'Detailed gradients: {gradients}')  # Only shows when debugging
        ```
        This separation of concerns improves readability according to MLOps best practices [*2](https://mlops.org/logging-best-practices).

        3. For AeroTune specifically, utilize the built-in MetricsLogger:
        ```python
        from aerotune.logging import MetricsLogger
        
        metrics_logger = MetricsLogger(log_dir='./logs')
        metrics_logger.log_metrics({'loss': loss, 'accuracy': acc}, step=global_step)
        ```
        The MetricsLogger automatically formats and organizes training metrics as documented in the AeroTune library [*3](https://aerotune.docs/metrics-logging)."

5. **Anticipate Follow-up Needs**
    - "Additionally, for visualizing these logs, I recommend:
        - Using TensorBoard for real-time monitoring of your training metrics [*4](https://tensorboard.dev)
        - Implementing log rotation to prevent massive log files [*5](https://docs.python.org/3/library/logging.handlers.html)
        - Creating a simple dashboard with the AeroTune Visualization package as described in their documentation [*6](https://aerotune.docs/visualization)"

---

## Additional Best Practices

### Handling Contradictory Information
- Explicitly note contradictions between sources: "While source [*1] recommends X approach, more recent documentation [*2] suggests Y method instead."
- Evaluate reliability of contradicting sources based on recency, authority, and relevance
- Present balanced information with appropriate weight given to more reliable sources
- Make clear recommendations despite contradictions, explaining your reasoning

### Managing Information Overload
- Prioritize information based on direct relevance to the user's query
- Organize findings into clear hierarchical sections with headers
- Use bullet points and formatting to highlight key information
- Present complex technical details after addressing the main question

### Effectively Using Multiple Tool Sessions
- Begin with broader searches, then narrow focus based on initial findings
- Use browsing sessions to verify claims found in search results
- Return to search with new terminology or concepts discovered during browsing
- Create a logical flow of investigation that builds toward a comprehensive answer

### Final Quality Check
- Ensure all claims are supported by properly formatted citations
- Verify that all aspects of the original query have been addressed
- Check that the information is presented in a logical, easy-to-follow sequence
- Confirm that practical, actionable recommendations are clearly highlighted        

</tool_use_instructions>"""

def get_tool_definitions(without_human_fallback: bool = False) -> List[Dict[str, Any]]:
    """
    Get all function definitions for OpenAI function calling.
    Centralizes all tool definitions in one place for better maintainability.

    Returns:
        List[Dict[str, Any]]: A list of tool definitions in OpenAI function calling format.
    """
    # Web Search Tool
    web_search_tool = {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": WEB_SEARCH_TOOL_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": WEB_SEARCH_TOOL_PARAMETERS_DESCRIPTION["query"]
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            },
            "strict": False
        }
    }
    # Web Browsing Tool
    web_browsing_tool = {
        "type": "function",
        "function": {
            "name": "web_browsing",
            "description": WEB_BROWSING_TOOL_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION["url"]
                    },
                    "query": {
                        "type": "string",
                        "description": WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION["query"]
                    }
                },
                "required": ["url", "query"],
                "additionalProperties": False
            },
            "strict": False
        }
    }
    # Need-Asking-Human Tool (Fallback)
    need_ask_human_tool = {
        "type": "function",
        "function": {
            "name": "need_ask_human",
            "description": NEED_ASK_HUMAN_TOOL_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "clarification_points": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": NEED_ASK_HUMAN_TOOL_PARAMETERS_DESCRIPTION["clarification_points"]
                    }
                },
                "required": ["clarification_points"],
                "additionalProperties": False
            },
            "strict": False
        }
    }
    tool_definitions = [web_search_tool, web_browsing_tool]
    if not without_human_fallback:
        tool_definitions.append(need_ask_human_tool)
    return tool_definitions

def get_gemini_tool_definitions(without_human_fallback: bool = False) -> types.Tool:
    """
    Get all function definitions for Gemini API function calling.
    Centralizes all tool definitions in one place for better maintainability.

    Returns:
        List[types.Tool]: A list of tool definitions in Gemini API format.
    """
    # Web Search Tool Definition
    web_search_function = types.FunctionDeclaration(
        name="web_search",
        description=WEB_SEARCH_TOOL_DESCRIPTION,
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "query": types.Schema(
                    type="STRING",
                    description=WEB_SEARCH_TOOL_PARAMETERS_DESCRIPTION["query"],
                ),
            },
            required=["query"],
        ),
    )

    # Web Browsing Tool Definition
    web_browsing_function = types.FunctionDeclaration(
        name="web_browsing",
        description=WEB_BROWSING_TOOL_DESCRIPTION,
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "url": types.Schema(
                    type="STRING",
                    description=WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION["url"],
                ),
                "query": types.Schema(
                    type="STRING",
                    description=WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION["query"],
                ),
            },
            required=["url", "query"],
        ),
    )

    # Need-Asking-Human Tool Definition for Gemini API
    need_ask_human_function = types.FunctionDeclaration(
        name="need_ask_human",
        description=NEED_ASK_HUMAN_TOOL_DESCRIPTION,
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "clarification_points": types.Schema(
                    type="ARRAY",
                    items=types.Schema(
                        type="STRING",
                    ),
                    description=NEED_ASK_HUMAN_TOOL_PARAMETERS_DESCRIPTION["clarification_points"],
                )
            },
            required=["clarification_points"],
        ),
    )

    tool_definitions = [web_search_function, web_browsing_function]


    if not without_human_fallback:
        tool_definitions.append(need_ask_human_function)

    return types.Tool(function_declarations=tool_definitions)

def get_anthropic_tool_definitions(without_human_fallback: bool = False) -> List[Dict[str, Any]]:
    """
    Get all function definitions for Anthropic Claude API function calling.
    Centralizes all tool definitions in one place for better maintainability.

    Returns:
        List[Dict[str, Any]]: A list of tool definitions in Anthropic Claude API format.
    """
    # Web Search Tool
    web_search_tool = {
        "name": "web_search",
        "description": WEB_SEARCH_TOOL_DESCRIPTION,
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": WEB_SEARCH_TOOL_PARAMETERS_DESCRIPTION["query"]
                }
            },
            "required": ["query"]
        }
    }
    
    # Web Browsing Tool
    web_browsing_tool = {
        "name": "web_browsing",
        "description": WEB_BROWSING_TOOL_DESCRIPTION,
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION["url"]
                },
                "query": {
                    "type": "string",
                    "description": WEB_BROWSING_TOOL_PARAMETERS_DESCRIPTION["query"]
                }
            },
            "required": ["url", "query"]
        }
    }
    
    # Need-Asking-Human Tool (Fallback)
    need_ask_human_tool = {
        "name": "need_ask_human",
        "description": NEED_ASK_HUMAN_TOOL_DESCRIPTION,
        "input_schema": {
            "type": "object",
            "properties": {
                "clarification_points": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": NEED_ASK_HUMAN_TOOL_PARAMETERS_DESCRIPTION["clarification_points"]
                }
            },
            "required": ["clarification_points"]
        }
    }
    
    tool_definitions = [web_search_tool, web_browsing_tool]
    if not without_human_fallback:
        tool_definitions.append(need_ask_human_tool)
    
    return tool_definitions