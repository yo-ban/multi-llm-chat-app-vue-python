async def need_ask_human(clarification_points: list[str]) -> str:
    """
    This tool is used for scenarios such as casual greetings or ambiguous queries that require clarification. 
    It accepts a single parameter, 'clarification_points', which is a list of specific follow-up questions addressing multiple aspects 
    that the user might be interested in. These prompts help guide the user in providing more detailed information.
    """
    if clarification_points:
        response = (
            "Web action was not executed because additional information is needed. "
            "Ask the user to clarify the following points:\n"
        )
        # Assemble a numbered list of clarification points.
        for i, point in enumerate(clarification_points, start=1):
            response += f"{i}. {point}\n"
        return response
    else:
        return (
            "Web action was not executed because additional information is needed. "
            "Ask the user to enter further details."
        )