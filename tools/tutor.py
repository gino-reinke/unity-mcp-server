"""Tutor/Learning mode tools and prompts."""


def register(mcp, config):
    """Register tutor mode tools and prompts."""

    @mcp.tool()
    def toggle_learning_mode(enable: bool = True) -> str:
        """Toggle Learning/Tutor Mode on or off.
        When enabled, the assistant shifts to an educational style:
        explaining concepts step-by-step, providing examples, asking
        comprehension questions, and referencing Unity documentation.
        Call with enable=true to activate, enable=false to deactivate."""
        config.learning_mode = enable
        if enable:
            return (
                "Learning Mode ACTIVATED.\n\n"
                "I will now:\n"
                "- Explain concepts step-by-step before writing code\n"
                "- Provide annotated examples with comments\n"
                "- Ask comprehension questions to check understanding\n"
                "- Reference official Unity documentation\n"
                "- Break complex topics into digestible pieces\n"
                "- Explain the 'why' behind every decision\n\n"
                "What would you like to learn about?"
            )
        return (
            "Learning Mode DEACTIVATED.\n"
            "Returning to standard assistant mode — "
            "I'll focus on efficiency and direct solutions."
        )

    @mcp.tool()
    def get_learning_status() -> str:
        """Check whether Learning/Tutor Mode is currently active."""
        if config.learning_mode:
            return "Learning Mode is ON. I'm explaining concepts in educational detail."
        return "Learning Mode is OFF. I'm in standard assistant mode."

    @mcp.tool()
    def explain_unity_concept(concept: str) -> str:
        """Request a detailed educational explanation of a Unity concept.
        Automatically activates learning mode for the explanation.
        Examples: 'MonoBehaviour lifecycle', 'coroutines vs async',
        'ScriptableObjects', 'ECS', 'physics raycasting'"""
        config.learning_mode = True
        return (
            f"Learning Mode activated for concept:{concept}\n\n"
            f"Please provide a comprehensive educational explanation of '{concept}' "
            f"following this structure:\n"
            f"1. What it is (definition in simple terms)\n"
            f"2. Why it matters (when and why you'd use it)\n"
            f"3. How it works (technical explanation with Unity specifics)\n"
            f"4. Code example (annotated C# with detailed comments)\n"
            f"5. Common pitfalls and best practices\n"
            f"6. Related concepts to explore next\n"
            f"7. Comprehension check question\n\n"
            f"Reference official Unity documentation where applicable."
        )

    @mcp.prompt()
    def unity_tutor(topic: str = "general Unity development") -> str:
        """Activate the Unity Tutor persona for guided learning.
        Select this prompt from the prompt picker in Claude Desktop
        to start an educational session on any Unity topic."""
        config.learning_mode = True
        return (
            f"You are an expert Unity game development tutor. The student wants "
            f"to learn about:{topic}\n\n"
            f"TEACHING GUIDELINES:\n"
            f"- Start by assessing what the student already knows\n"
            f"- Break the topic into 3-5 key concepts to cover\n"
            f"- For each concept: explain simply, show a C# code example, "
            f"then ask a comprehension question before moving on\n"
            f"- Use analogies from everyday life to explain abstract concepts\n"
            f"- Reference docs.unity3d.com for API details\n"
            f"- After covering all concepts, provide a mini-challenge that "
            f"combines everything learned\n"
            f"- Be encouraging and patient — celebrate understanding\n"
            f"- If you use the search tools, share the relevant documentation links\n\n"
            f"Begin by introducing the topic and asking the student what they "
            f"already know about{topic}."
        )

    @mcp.prompt()
    def unity_code_review(script_path: str = "") -> str:
        """Start an educational code review session for a Unity C# script.
        The agent will read the script and explain it line by line."""
        return (
            f"Please perform an educational code review of the Unity C# script "
            f"at path:{script_path}\n\n"
            f"First, use the read_file tool to load the script. Then:\n"
            f"1. Summarize what the script does in plain English\n"
            f"2. Walk through the code section by section, explaining each part\n"
            f"3. Identify any bugs, performance issues, or anti-patterns\n"
            f"4. Suggest improvements with explanations of why they're better\n"
            f"5. Rate the code quality (1-10) with justification\n"
            f"6. Ask the student if they have questions about any part"
        )