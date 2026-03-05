"""
Service for managing default thinking protocols.
Creates the standard protocols on first startup.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.thinking_protocol import ThinkingProtocol


DEFAULT_PROTOCOLS = [
    {
        "name": "Standard Problem Solving",
        "description": "Universal step-by-step reasoning: pick a task → analyze → plan → implement in a loop → output result",
        "type": "standard",
        "is_default": True,
        "steps": [
            {
                "id": "s_0_todo",
                "type": "todo",
                "name": "Create Task List",
                "category": "planning",
                "instruction": "Break down the request into clear, actionable tasks. Create a structured todo list to track progress through each task.",
            },
            {
                "id": "s_1_analyze",
                "type": "action",
                "name": "Analyze Requirements",
                "category": "analysis",
                "instruction": "Carefully read and understand what is being asked. Identify:\n- Inputs and expected outputs\n- Constraints and limitations\n- Success criteria\n- Edge cases to consider",
            },
            {
                "id": "s_2_plan",
                "type": "action",
                "name": "Propose Solutions",
                "category": "planning",
                "instruction": "Generate 2-3 possible approaches to solve the problem. For each approach:\n- Describe the strategy briefly\n- List pros and cons\n- Estimate complexity\nChoose the best approach and explain why.",
            },
            {
                "id": "s_3_loop",
                "type": "loop",
                "name": "Implementation Cycle",
                "category": "execution",
                "instruction": "Iteratively implement and refine the solution until it meets the success criteria or maximum iterations are reached.",
                "max_iterations": 5,
                "exit_condition": "Solution passes all checks and meets success criteria",
                "steps": [
                    {
                        "id": "s_3_0_impl",
                        "type": "action",
                        "name": "Implement",
                        "instruction": "Execute the chosen approach. Write code, produce output, or perform the required action. Focus on correctness first, then optimize.",
                    },
                    {
                        "id": "s_3_1_verify",
                        "type": "action",
                        "name": "Verify",
                        "instruction": "Check the result against success criteria. Look for errors, edge cases, and missing requirements. Test with different inputs if applicable.",
                    },
                    {
                        "id": "s_3_2_decide",
                        "type": "decision",
                        "name": "Evaluate Result",
                        "instruction": "Does the solution meet all requirements?",
                        "exit_condition": "If YES → exit loop and proceed to output. If NO → identify what needs to change and continue loop.",
                    },
                ],
            },
            {
                "id": "s_4_output",
                "type": "action",
                "name": "Output Result",
                "category": "output",
                "instruction": "Present the final result clearly:\n- Summarize what was done\n- Show the solution/output\n- Note any limitations or caveats\n- Suggest follow-up actions if relevant",
            },
        ],
    },
    {
        "name": "Research & Analysis",
        "description": "Deep research protocol: gather information → analyze → synthesize → conclude",
        "type": "standard",
        "is_default": False,
        "steps": [
            {
                "id": "r_0_scope",
                "type": "action",
                "name": "Define Scope",
                "category": "planning",
                "instruction": "Clearly define the research question or analysis goal. Identify what information is needed and what sources to use.",
            },
            {
                "id": "r_1_gather",
                "type": "loop",
                "name": "Information Gathering",
                "category": "execution",
                "instruction": "Collect relevant information from available sources.",
                "max_iterations": 3,
                "exit_condition": "Sufficient information gathered to answer the question",
                "steps": [
                    {
                        "id": "r_1_0_search",
                        "type": "action",
                        "name": "Search & Read",
                        "instruction": "Search for relevant information. Read and extract key facts, data points, and perspectives.",
                    },
                    {
                        "id": "r_1_1_check",
                        "type": "decision",
                        "name": "Sufficiency Check",
                        "instruction": "Is there enough information to form a well-supported conclusion?",
                        "exit_condition": "If YES → exit loop. If NO → identify gaps and search for more.",
                    },
                ],
            },
            {
                "id": "r_2_analyze",
                "type": "action",
                "name": "Analyze & Synthesize",
                "category": "analysis",
                "instruction": "Organize and analyze the gathered information:\n- Identify patterns and trends\n- Compare different perspectives\n- Note contradictions or gaps\n- Draw connections between data points",
            },
            {
                "id": "r_3_conclude",
                "type": "action",
                "name": "Formulate Conclusions",
                "category": "output",
                "instruction": "Present clear, well-supported conclusions:\n- State main findings\n- Provide evidence and reasoning\n- Acknowledge uncertainties\n- Recommend next steps",
            },
        ],
    },
    {
        "name": "Adaptive Orchestrator",
        "description": "Meta-protocol that analyzes the task and delegates to the most appropriate child protocol",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "o_0_classify",
                "type": "action",
                "name": "Classify Task",
                "category": "analysis",
                "instruction": "Analyze the incoming task or query. Determine its nature:\n- Is it a problem to solve? (coding, debugging, design)\n- Is it a research/analysis question?\n- Is it a creative/generation task?\n- Is it a multi-step project?\nClassify the task type and complexity.",
            },
            {
                "id": "o_1_select",
                "type": "decision",
                "name": "Select Strategy",
                "category": "planning",
                "instruction": "Based on the task classification, decide which thinking protocol is best suited. Consider:\n- Task complexity and type\n- Available protocols and their strengths\n- Whether the task needs iterative refinement or deep research",
                "exit_condition": "Protocol selected based on task type",
            },
            {
                "id": "o_2_delegate",
                "type": "delegate",
                "name": "Execute Protocol",
                "category": "execution",
                "instruction": "Delegate execution to the selected child protocol. The chosen protocol will handle the actual reasoning and problem-solving process.",
                "protocol_ids": [],
            },
            {
                "id": "o_3_review",
                "type": "action",
                "name": "Review & Synthesize",
                "category": "verification",
                "instruction": "Review the output from the delegated protocol:\n- Does the result fully address the original task?\n- Is the quality sufficient?\n- Should a different protocol be tried?\nIf unsatisfied, consider re-delegating to another protocol or refining the result.",
            },
        ],
    },
]


async def create_default_protocols(db: AsyncSession):
    """Create default thinking protocols if they don't exist."""
    result = await db.execute(select(ThinkingProtocol).limit(1))
    if result.scalar_one_or_none():
        return  # Protocols already exist

    # First pass: create all protocols
    proto_map = {}  # name -> ThinkingProtocol instance
    for proto_data in DEFAULT_PROTOCOLS:
        proto = ThinkingProtocol(
            name=proto_data["name"],
            description=proto_data["description"],
            type=proto_data.get("type", "standard"),
            steps=proto_data["steps"],
            is_default=proto_data.get("is_default", False),
        )
        db.add(proto)
        proto_map[proto_data["name"]] = proto

    await db.flush()

    # Second pass: wire orchestrator delegate steps to actual protocol IDs
    orchestrator = proto_map.get("Adaptive Orchestrator")
    if orchestrator:
        standard_ids = [
            str(p.id) for name, p in proto_map.items()
            if p.type != "orchestrator"
        ]
        steps = list(orchestrator.steps)
        for step in steps:
            if step.get("type") == "delegate":
                step["protocol_ids"] = standard_ids
        orchestrator.steps = steps

    await db.commit()
