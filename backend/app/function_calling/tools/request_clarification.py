async def request_clarification(clarification_points: list[str]) -> str:
    """
    Propose specific suggestions or questions to help the user refine and specify their vague or ambiguous request.
    - Purpose: Perform targeted searches to obtain relevant URLs and concise summaries.
    - Usage Guidelines:
        - **Focus on one topic per search query** (split searches when multiple pieces of information are needed)
        - **Formulate clear, specific queries** based on the exact information needed, rather than copying the user's question verbatim
        - If initial results are insufficient, **strategically plan multiple searches** with refined queries
        - Consider date-restricted searches when information might be outdated or when recent data is required

    Args:
        clarification_points: A list of specific suggestions or questions to present to the user to help them clarify their request.

    Returns:
        str: An instruction to the LLM on how to ask the user for clarification.
    """
    if clarification_points:
        # Construct the instruction for the LLM
        response = "The user's request is unclear or lacks sufficient detail. Ask the user to clarify their request, focusing on the following aspects or suggestions:\n"
        # Assemble a numbered list of points for the LLM to use when asking the user.
        for i, point in enumerate(clarification_points, start=1):
            response += f"{i}. {point}\n"
        
        response += "\n\nIf the content has already been sent once, there is no need to duplicate it."
        return response
    else:
        # Fallback instruction for the LLM if no specific points were generated.
        return (
            "The user's request is too vague. Ask the user to provide more specific details about what they need."
        ) 