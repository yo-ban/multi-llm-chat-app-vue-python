import sys
import json
from pathlib import Path
from pprint import pprint

# Add the parent directory to the Python path to import app modules
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.function_calling.definitions import (
    generate_tool_definition,
    get_tool_definitions,
    get_available_tools
)


def test_tool_definition_generation():
    """Test the tool definition generation functionality."""
    print("\n=== Testing tool definition generation ===\n")
    
    # Get all available tools
    tools = get_available_tools()
    print(f"Available tools: {', '.join([t.__name__ for t in tools])}")
    
    # Generate and print canonical definition for each tool
    for tool in tools:
        print(f"\n=== Canonical definition for {tool.__name__} ===")
        definition = generate_tool_definition(tool)
        pprint(definition)
    
    # Test vendor-specific formats
    print("\n=== OpenAI format ===")
    openai_defs = get_tool_definitions(vendor="openai")
    print(f"Generated {len(openai_defs)} OpenAI tool definitions")
    print(json.dumps(openai_defs, indent=2))
    
    print("\n=== Anthropic format ===")
    anthropic_defs = get_tool_definitions(vendor="anthropic")
    print(f"Generated {len(anthropic_defs)} Anthropic tool definitions")
    print(json.dumps(anthropic_defs, indent=2))
    
    print("\n=== Gemini format ===")
    gemini_defs = get_tool_definitions(vendor="gemini")
    print(f"Generated Gemini tool definitions with {len(gemini_defs.function_declarations)} functions")
    
    print("\n=== Test excluding fallback tool ===")
    limited_defs = get_tool_definitions(without_human_fallback=True)
    print(f"Generated {len(limited_defs)} definitions (without human fallback)")
    
    print("\nAll tests completed successfully!")


if __name__ == "__main__":
    test_tool_definition_generation() 