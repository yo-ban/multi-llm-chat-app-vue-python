async def task_planning(plans: list[str]) -> dict:
    """
    A tool for recording the task plan, available only during the current turn.
    Use this to write down the specific plan or steps before executing tasks that require multiple steps or tool calls.
    - Usage Guidelines:
        - Describe the necessary steps or thought process for the task execution in the `plan` argument.
        - Clarify the plan using this tool before invoking other tools.
        - Keep the plan concise; the content will be discarded after the current response cycle is complete.

    Args:
        plans: List of text describing the plan or steps for the task to be executed.

    Returns:
        dict: Status information confirming that the plan was recorded. {"status": "success"}
    """
    return { "status": "success" }