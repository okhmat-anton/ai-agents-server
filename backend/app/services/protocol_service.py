"""
Service for managing default thinking protocols.
Creates the standard protocols on first startup.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.mongodb.models import MongoThinkingProtocol
from app.mongodb.services import ThinkingProtocolService, AgentProtocolService


DEFAULT_PROTOCOLS = [
    # ═══════════════════════════════════════════════════════════
    # LOW-LEVEL SPECIALIZED PROTOCOLS
    # ═══════════════════════════════════════════════════════════
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
        "name": "Programmer",
        "description": "Write clean, tested code — translates specifications into working implementation",
        "type": "standard",
        "is_default": False,
        "steps": [
            {
                "id": "prog_0_understand",
                "type": "action",
                "name": "Understand Requirements",
                "category": "analysis",
                "instruction": "Parse the task specification. Identify:\n- Programming language / framework\n- Input/output contract\n- Performance requirements\n- Dependencies and integrations\n- Coding style and conventions to follow",
            },
            {
                "id": "prog_1_design",
                "type": "action",
                "name": "Design Solution",
                "category": "planning",
                "instruction": "Design the solution architecture:\n- Data structures and models\n- Key functions/classes and their responsibilities\n- API contracts if applicable\n- Error handling strategy\nKeep it simple — avoid over-engineering.",
            },
            {
                "id": "prog_2_implement",
                "type": "loop",
                "name": "Code & Refine",
                "category": "execution",
                "instruction": "Write the code iteratively. Each iteration should produce working code.",
                "max_iterations": 3,
                "exit_condition": "Code is complete, handles edge cases, and follows best practices",
                "steps": [
                    {
                        "id": "prog_2_0_write",
                        "type": "action",
                        "name": "Write Code",
                        "instruction": "Implement the solution. Write clear, well-commented code. Use meaningful variable names. Follow the language's idioms and conventions.",
                    },
                    {
                        "id": "prog_2_1_review",
                        "type": "action",
                        "name": "Self-Review",
                        "instruction": "Review your own code:\n- Are there bugs or logic errors?\n- Are edge cases handled?\n- Is error handling sufficient?\n- Is the code readable and maintainable?\n- Are there any security concerns?",
                    },
                    {
                        "id": "prog_2_2_check",
                        "type": "decision",
                        "name": "Quality Check",
                        "instruction": "Is the code production-ready?",
                        "exit_condition": "If YES → exit. If NO → fix issues and iterate.",
                    },
                ],
            },
            {
                "id": "prog_3_deliver",
                "type": "action",
                "name": "Deliver Code",
                "category": "output",
                "instruction": "Present the final code:\n- Use project_file_write skill to save code files\n- Explain key design decisions\n- Document usage (how to run, API endpoints, etc.)\n- Note any TODOs or known limitations\n\nSignal completion: <<<DELEGATE_DONE:Code implemented and saved>>>",
            },
        ],
    },
    {
        "name": "Tester",
        "description": "Verify correctness — write and run tests, check edge cases, ensure quality",
        "type": "standard",
        "is_default": False,
        "steps": [
            {
                "id": "test_0_analyze",
                "type": "action",
                "name": "Analyze What to Test",
                "category": "analysis",
                "instruction": "Examine the code/feature to be tested:\n- Read existing code using project_file_read or file_read skills\n- Identify all public interfaces and functions\n- Map out normal flows, edge cases, and error scenarios\n- Determine test strategy (unit, integration, E2E)",
            },
            {
                "id": "test_1_write",
                "type": "action",
                "name": "Write Tests",
                "category": "execution",
                "instruction": "Create comprehensive test cases:\n- Happy path tests for core functionality\n- Edge case tests (empty input, large input, null values)\n- Error handling tests (invalid input, missing dependencies)\n- Boundary condition tests\nSave test files using project_file_write skill.",
            },
            {
                "id": "test_2_run",
                "type": "loop",
                "name": "Test Execution Cycle",
                "category": "execution",
                "instruction": "Run tests and fix any issues found.",
                "max_iterations": 3,
                "exit_condition": "All tests pass or critical issues are documented",
                "steps": [
                    {
                        "id": "test_2_0_exec",
                        "type": "action",
                        "name": "Run Tests",
                        "instruction": "Execute the tests using shell_exec or code_execute skill. Collect results: passed, failed, errors.",
                    },
                    {
                        "id": "test_2_1_eval",
                        "type": "decision",
                        "name": "Evaluate Results",
                        "instruction": "Did all tests pass? Are there failures that indicate real bugs vs test issues?",
                        "exit_condition": "If all pass → exit. If failures → analyze and either fix test or report bug.",
                    },
                ],
            },
            {
                "id": "test_3_report",
                "type": "action",
                "name": "Test Report",
                "category": "output",
                "instruction": "Deliver a test report:\n- Total tests: passed / failed / skipped\n- Coverage of key scenarios\n- Bugs found (if any) with reproduction steps\n- Recommendations for additional testing\n\nSignal completion: <<<DELEGATE_DONE:Testing complete — X/Y tests passed>>>",
            },
        ],
    },
    {
        "name": "Code Reviewer",
        "description": "Review code for quality, correctness, security, and best practices",
        "type": "standard",
        "is_default": False,
        "steps": [
            {
                "id": "rev_0_read",
                "type": "action",
                "name": "Read Code",
                "category": "analysis",
                "instruction": "Read all relevant code files using project_file_read or file_read skills. Understand:\n- Overall architecture and design patterns\n- Data flow and control flow\n- Dependencies and imports\n- Configuration and environment usage",
            },
            {
                "id": "rev_1_check",
                "type": "action",
                "name": "Quality Analysis",
                "category": "analysis",
                "instruction": "Evaluate the code on multiple dimensions:\n- **Correctness**: Logic errors, off-by-one, race conditions\n- **Security**: Injection, auth bypass, data exposure, path traversal\n- **Performance**: N+1 queries, unnecessary allocations, blocking I/O\n- **Readability**: Naming, structure, comments, complexity\n- **Maintainability**: SOLID principles, DRY, proper abstractions\n- **Error Handling**: Missing try/catch, unhandled edge cases",
            },
            {
                "id": "rev_2_report",
                "type": "action",
                "name": "Review Report",
                "category": "output",
                "instruction": "Produce a structured code review:\n- **Critical issues** (must fix before merge)\n- **Warnings** (should fix, potential problems)\n- **Suggestions** (nice-to-have improvements)\n- **Positive notes** (good practices observed)\n\nFor each issue: file, line/area, description, suggested fix.\n\nSignal completion: <<<DELEGATE_DONE:Code review complete — N critical, M warnings>>>",
            },
        ],
    },
    {
        "name": "Creative Writer",
        "description": "Generate creative content — texts, ideas, narratives, brainstorming",
        "type": "standard",
        "is_default": False,
        "steps": [
            {
                "id": "cw_0_brief",
                "type": "action",
                "name": "Understand Brief",
                "category": "analysis",
                "instruction": "Analyze the creative brief:\n- Content type (article, story, copy, brainstorm, etc.)\n- Target audience\n- Tone and style requirements\n- Length and format constraints\n- Key messages or themes to convey",
            },
            {
                "id": "cw_1_ideate",
                "type": "action",
                "name": "Ideation",
                "category": "planning",
                "instruction": "Generate multiple creative directions:\n- Brainstorm 3-5 different angles or approaches\n- Consider unexpected perspectives\n- Think about emotional resonance\n- Select the strongest direction and explain why",
            },
            {
                "id": "cw_2_create",
                "type": "loop",
                "name": "Draft & Refine",
                "category": "execution",
                "instruction": "Create the content iteratively, refining with each pass.",
                "max_iterations": 3,
                "exit_condition": "Content meets the brief requirements and quality bar",
                "steps": [
                    {
                        "id": "cw_2_0_draft",
                        "type": "action",
                        "name": "Draft",
                        "instruction": "Write the content. Focus on capturing the right tone, delivering key messages, and engaging the audience.",
                    },
                    {
                        "id": "cw_2_1_polish",
                        "type": "action",
                        "name": "Polish",
                        "instruction": "Refine the draft:\n- Improve flow and readability\n- Strengthen weak sections\n- Eliminate redundancy\n- Ensure consistency of voice and style",
                    },
                ],
            },
            {
                "id": "cw_3_deliver",
                "type": "action",
                "name": "Deliver Content",
                "category": "output",
                "instruction": "Present the final content with:\n- The finished piece\n- Brief notes on creative choices made\n- Suggestions for variations or follow-up content\n\nSignal completion: <<<DELEGATE_DONE:Content created>>>",
            },
        ],
    },

    {
        "name": "Deep Task Decomposition",
        "description": "Break down complex tasks into atomic sub-tasks — eat the elephant piece by piece. Recursively decomposes until every item is a simple, concrete action.",
        "type": "standard",
        "is_default": False,
        "steps": [
            {
                "id": "dtd_0_understand",
                "type": "action",
                "name": "Understand the Goal",
                "category": "analysis",
                "model_role": "task_decomposition",
                "instruction": (
                    "Analyze the task at a high level:\n"
                    "1. **What** is the end goal? What does 'done' look like?\n"
                    "2. **Why** is this needed? Understanding purpose helps decompose correctly.\n"
                    "3. **Scope** — What is included and what is explicitly out of scope?\n"
                    "4. **Constraints** — Time, technology, dependencies, prerequisites.\n"
                    "5. **Inputs available** — What do we already have to work with?\n"
                    "6. **Risks** — What could go wrong? What unknowns exist?\n"
                    "\n"
                    "Complexity assessment:\n"
                    "  - **Trivial** → No decomposition needed, just do it.\n"
                    "  - **Simple** → 2-5 clear steps, light decomposition.\n"
                    "  - **Medium** → Multiple components, needs structured breakdown.\n"
                    "  - **Complex** → Multiple layers, cross-cutting concerns, deep decomposition required."
                ),
            },
            {
                "id": "dtd_1_first_level",
                "type": "action",
                "name": "First Level Breakdown",
                "category": "planning",
                "model_role": "task_decomposition",
                "instruction": (
                    "Break the task into major components or phases (3-7 top-level items).\n"
                    "Each component should represent a distinct, meaningful chunk of work.\n"
                    "\n"
                    "For each component identify:\n"
                    "- **Name** — Short, descriptive label\n"
                    "- **Purpose** — What this component achieves\n"
                    "- **Dependencies** — What must be done before this\n"
                    "- **Estimated complexity** — Trivial / Simple / Medium / Complex\n"
                    "\n"
                    "Order components by dependency (things that need to happen first go first).\n"
                    "This is the skeleton — we will decompose each component further."
                ),
            },
            {
                "id": "dtd_2_deep_loop",
                "type": "loop",
                "name": "Deep Decomposition",
                "category": "planning",
                "instruction": "For each component marked as Medium or Complex, recursively break it down further until every sub-task is atomic.",
                "max_iterations": 5,
                "exit_condition": "Every item in the task list is an atomic action (can be done in 1-2 simple steps with no ambiguity)",
                "steps": [
                    {
                        "id": "dtd_2_0_decompose",
                        "type": "action",
                        "name": "Decompose Next Component",
                        "model_role": "task_decomposition",
                        "instruction": (
                            "Take the next non-atomic component and break it into smaller sub-tasks.\n"
                            "\n"
                            "**Atomic task criteria** — a task is atomic when:\n"
                            "- It can be completed in one sitting (minutes, not hours)\n"
                            "- It has a single, clear action (create, read, write, configure, test, etc.)\n"
                            "- The expected output is obvious and verifiable\n"
                            "- No further decisions are needed to execute it\n"
                            "- A junior developer or a focused AI could do it without asking questions\n"
                            "\n"
                            "**Decomposition rules:**\n"
                            "- Each sub-task should be 1 concrete action (not 'implement feature X' but 'create file Y with function Z')\n"
                            "- Include verification steps (e.g., 'run tests', 'check output', 'verify file exists')\n"
                            "- Name tasks as imperative verbs: Create, Write, Add, Configure, Test, Verify, Update\n"
                            "- Preserve dependency order within the component\n"
                            "- If a sub-task is still complex, mark it for further decomposition"
                        ),
                    },
                    {
                        "id": "dtd_2_1_check",
                        "type": "decision",
                        "name": "All Tasks Atomic?",
                        "instruction": "Review the full task list. Are there any remaining items that are not atomic (still too vague, too large, or require further decisions)?",
                        "exit_condition": "If ALL tasks are atomic → exit loop. If any tasks are still complex → continue decomposing.",
                    },
                ],
            },
            {
                "id": "dtd_3_build_plan",
                "type": "todo",
                "name": "Build Execution Plan",
                "category": "planning",
                "instruction": (
                    "Convert the fully decomposed task tree into a flat, ordered execution plan.\n"
                    "\n"
                    "Ordering rules:\n"
                    "- Respect dependencies (prerequisites first)\n"
                    "- Group related tasks together\n"
                    "- Place verification/test steps right after the thing they verify\n"
                    "- Number every task sequentially\n"
                    "\n"
                    "Each task in the todo list should be:\n"
                    "- A single atomic action\n"
                    "- Phrased as an imperative (e.g., 'Create utils.py with helper functions')\n"
                    "- Self-contained — readable without needing surrounding context"
                ),
            },
            {
                "id": "dtd_4_execute",
                "type": "loop",
                "name": "Execute Tasks",
                "category": "execution",
                "instruction": "Work through the todo list task by task. Mark each as done when complete. If a task reveals unexpected complexity, decompose it further before continuing.",
                "max_iterations": 20,
                "exit_condition": "All tasks in the todo list are done or skipped",
                "steps": [
                    {
                        "id": "dtd_4_0_do",
                        "type": "action",
                        "name": "Execute Next Task",
                        "instruction": "Pick the next pending task from the todo list. Execute it. Mark it as done. Update the todo list. If the task is blocked, skip it and note why.",
                    },
                    {
                        "id": "dtd_4_1_verify",
                        "type": "decision",
                        "name": "Check Progress",
                        "instruction": "Is the todo list complete? Are there any blocked or failed tasks that need replanning?",
                        "exit_condition": "If all done → exit. If blocked tasks remain → add decomposed alternatives and continue.",
                    },
                ],
            },
            {
                "id": "dtd_5_summary",
                "type": "action",
                "name": "Deliver Results",
                "category": "output",
                "instruction": (
                    "Present the final results:\n"
                    "1. **Summary** — What was accomplished\n"
                    "2. **Task breakdown** — The decomposition tree (for reference)\n"
                    "3. **Deliverables** — Files created, code written, actions taken\n"
                    "4. **Issues encountered** — Anything that was harder than expected\n"
                    "5. **Remaining items** — Skipped/blocked tasks, if any\n"
                    "\n"
                    "Signal completion: <<<DELEGATE_DONE:Task decomposition and execution complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # MID-LEVEL ORCHESTRATORS
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Development Orchestrator",
        "description": "Mid-level orchestrator for software development: coordinates coding, testing, and code review",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "dev_0_analyze",
                "type": "action",
                "name": "Analyze Development Task",
                "category": "analysis",
                "instruction": "Understand the development request:\n- What needs to be built or changed?\n- What is the existing codebase state? (check files first)\n- What are the technical constraints?\n- How complex is this — simple feature, refactor, or new system?",
            },
            {
                "id": "dev_1_plan",
                "type": "todo",
                "name": "Create Development Plan",
                "category": "planning",
                "instruction": "Break down into development sub-tasks:\n1. Implementation (code writing)\n2. Testing (if applicable)\n3. Code review (if complex)\nCreate a structured todo list for tracking.",
            },
            {
                "id": "dev_2_code",
                "type": "delegate",
                "name": "Implement Code",
                "category": "execution",
                "instruction": "Delegate code implementation to the Programmer protocol. Provide clear specifications:\n- What to build\n- Expected behavior\n- Files and locations\n- Coding conventions to follow",
                "protocol_ids": [],  # Will be filled with Programmer protocol ID
            },
            {
                "id": "dev_3_test",
                "type": "delegate",
                "name": "Test Implementation",
                "category": "verification",
                "instruction": "Delegate testing to the Tester protocol. Specify:\n- What files to test\n- Expected behavior to verify\n- Edge cases to check\nSkip this step for trivial changes.",
                "protocol_ids": [],  # Will be filled with Tester protocol ID
            },
            {
                "id": "dev_4_review",
                "type": "delegate",
                "name": "Review Code Quality",
                "category": "verification",
                "instruction": "Delegate code review to the Code Reviewer protocol for complex changes. Specify:\n- Files to review\n- Key concerns (security, performance, etc.)\nSkip for simple/trivial changes.",
                "protocol_ids": [],  # Will be filled with Code Reviewer protocol ID
            },
            {
                "id": "dev_5_evaluate",
                "type": "loop",
                "name": "Evaluate & Iterate",
                "category": "verification",
                "instruction": "Review all results from coding, testing, and review. If there are issues, re-delegate to fix them.",
                "max_iterations": 2,
                "exit_condition": "All development sub-tasks completed successfully, no critical issues remain",
                "steps": [
                    {
                        "id": "dev_5_0_check",
                        "type": "decision",
                        "name": "Quality Gate",
                        "instruction": "Are all critical issues resolved? Is the code ready for delivery?",
                        "exit_condition": "If YES → deliver. If NO → delegate fixes to Programmer.",
                    },
                ],
            },
            {
                "id": "dev_6_deliver",
                "type": "action",
                "name": "Deliver Results",
                "category": "output",
                "instruction": "Summarize the development work:\n- What was implemented\n- Test results\n- Any remaining TODOs or known issues\n- Files changed\n\nSignal completion: <<<DELEGATE_DONE:Development complete>>>",
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # MASTER ORCHESTRATOR (TOP-LEVEL)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Master Orchestrator",
        "description": "Top-level orchestrator — analyzes user intent, decomposes complex tasks, delegates to specialized protocols (including mid-level orchestrators), evaluates results, and iterates until the task is fully complete",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "mo_0_intent",
                "type": "action",
                "name": "Understand User Intent",
                "category": "analysis",
                "instruction": (
                    "Deeply analyze the user's message to determine:\n"
                    "1. **Primary intent** — What does the user want? (build something, fix something, learn something, create content, analyze data, etc.)\n"
                    "2. **Scope** — Is this a simple question, a single task, or a complex multi-step project?\n"
                    "3. **Domain** — Software development, research, creative work, data analysis, system administration, general knowledge?\n"
                    "4. **Implicit needs** — What the user didn't say but probably expects (e.g., error handling, testing, documentation)\n"
                    "5. **Constraints** — Time, quality, technology, format preferences\n"
                    "\n"
                    "Classify complexity:\n"
                    "  - **Simple** (1 protocol): Direct answer, single-step task\n"
                    "  - **Medium** (1-2 protocols): Multi-step but single domain\n"
                    "  - **Complex** (2+ protocols, possibly hierarchical): Cross-domain, requires planning + multiple delegations"
                ),
            },
            {
                "id": "mo_1_plan",
                "type": "todo",
                "name": "Create Execution Plan",
                "category": "planning",
                "instruction": (
                    "Based on intent analysis, create a strategic plan:\n"
                    "- Break complex tasks into ordered sub-tasks\n"
                    "- For each sub-task, identify which protocol is best suited\n"
                    "- Consider dependencies between sub-tasks (what must happen first?)\n"
                    "- Identify where mid-level orchestrators should be used vs direct protocols\n"
                    "\n"
                    "Create a todo list that tracks the overall progress of all delegations."
                ),
            },
            {
                "id": "mo_2_decide",
                "type": "decision",
                "name": "Select Execution Strategy",
                "category": "planning",
                "instruction": (
                    "Choose the execution strategy:\n"
                    "\n"
                    "**A) Direct handling** — For simple questions, use your own knowledge and skills directly.\n"
                    "   → No delegation needed, just answer.\n"
                    "\n"
                    "**B) Single delegation** — For medium tasks in one domain:\n"
                    "   → Delegate to one specialized protocol (Programmer, Researcher, Writer, etc.)\n"
                    "\n"
                    "**C) Sequential delegation** — For complex tasks:\n"
                    "   → Delegate to multiple protocols in sequence, reviewing results between each\n"
                    "\n"
                    "**D) Orchestrator delegation** — For complex development tasks:\n"
                    "   → Delegate to a mid-level orchestrator (Development Orchestrator) which manages its own sub-delegations\n"
                    "\n"
                    "Explain your choice and proceed."
                ),
                "exit_condition": "Strategy selected, proceed to execution",
            },
            {
                "id": "mo_3_execute",
                "type": "delegate",
                "name": "Execute via Delegation",
                "category": "execution",
                "instruction": (
                    "Delegate to the selected protocol(s). For each delegation:\n"
                    "1. Provide clear, specific context about what needs to be done\n"
                    "2. Include any relevant constraints or requirements\n"
                    "3. Specify expected deliverables\n"
                    "\n"
                    "**Protocol selection guide:**\n"
                    "- Coding task → `Development Orchestrator` (complex) or `Programmer` (simple)\n"
                    "- Bug fixing → `Programmer` + optionally `Tester`\n"
                    "- Complex multi-step task → `Deep Task Decomposition`\n"
                    "- Research question → `Research & Analysis`\n"
                    "- General problem → `Standard Problem Solving`\n"
                    "- Creative writing → `Creative Writer`\n"
                    "- Code quality → `Code Reviewer`\n"
                    "- Testing → `Tester`\n"
                    "\n"
                    "After delegating, wait for <<<DELEGATE_DONE>>> to receive results."
                ),
                "protocol_ids": [],  # Will be filled with ALL protocol IDs
            },
            {
                "id": "mo_4_evaluate",
                "type": "loop",
                "name": "Evaluate & Iterate",
                "category": "verification",
                "instruction": "After each delegation completes, evaluate the results against the original intent.",
                "max_iterations": 3,
                "exit_condition": "All sub-tasks from the plan are completed successfully",
                "steps": [
                    {
                        "id": "mo_4_0_review",
                        "type": "action",
                        "name": "Review Results",
                        "instruction": (
                            "For each completed delegation:\n"
                            "- Does the result meet the requirements?\n"
                            "- Is the quality acceptable?\n"
                            "- Are there gaps or missing pieces?\n"
                            "- Should another protocol be invoked to complement?"
                        ),
                    },
                    {
                        "id": "mo_4_1_decide",
                        "type": "decision",
                        "name": "Next Action",
                        "instruction": (
                            "Based on review:\n"
                            "- **All done** → Exit loop, proceed to synthesis\n"
                            "- **Needs fixing** → Re-delegate to same protocol with feedback\n"
                            "- **Needs more work** → Delegate to next protocol in the plan\n"
                            "- **Wrong approach** → Try a different protocol\n"
                            "Update the todo list with status changes."
                        ),
                        "exit_condition": "All planned work complete and quality is sufficient → exit loop",
                    },
                ],
            },
            {
                "id": "mo_5_synthesize",
                "type": "action",
                "name": "Synthesize & Deliver",
                "category": "output",
                "instruction": (
                    "Compile the final response for the user:\n"
                    "1. **Summary** — What was accomplished (high-level)\n"
                    "2. **Details** — Key results from each delegation\n"
                    "3. **Deliverables** — Files created, code written, answers found\n"
                    "4. **Next steps** — Suggestions for follow-up or improvements\n"
                    "\n"
                    "Present it in a clear, user-friendly format.\n"
                    "The user should not need to understand the internal delegation mechanics."
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # SALES ORCHESTRATOR (AIS-70)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Sales Expert",
        "description": "Orchestrator for sales strategy: lead qualification, objection handling, deal closing, and relationship management",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "sales_0_assess",
                "type": "action",
                "name": "Assess Sales Situation",
                "category": "analysis",
                "instruction": (
                    "Analyze the sales scenario:\n"
                    "- What product/service is being sold?\n"
                    "- Who is the target customer (demographics, needs, pain points)?\n"
                    "- What stage of the sales funnel are we at (awareness, interest, decision, action)?\n"
                    "- What is the competitive landscape?\n"
                    "- What previous interactions or objections have occurred?"
                ),
            },
            {
                "id": "sales_1_plan",
                "type": "todo",
                "name": "Create Sales Strategy",
                "category": "planning",
                "instruction": (
                    "Build a sales action plan:\n"
                    "1. Define the value proposition for this specific customer\n"
                    "2. Identify key objections and prepare responses\n"
                    "3. Plan the conversation flow and closing strategy\n"
                    "4. Set follow-up milestones\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "sales_2_qualify",
                "type": "action",
                "name": "Qualify & Engage",
                "category": "execution",
                "instruction": (
                    "Execute the sales engagement:\n"
                    "- Qualify the lead (BANT: Budget, Authority, Need, Timeline)\n"
                    "- Present the value proposition tailored to their pain points\n"
                    "- Handle objections with empathy and evidence\n"
                    "- Use social proof and case studies where applicable\n"
                    "- Guide toward a decision with clear next steps"
                ),
            },
            {
                "id": "sales_3_evaluate",
                "type": "loop",
                "name": "Evaluate & Iterate",
                "category": "verification",
                "instruction": "Review the sales interaction and refine the approach.",
                "max_iterations": 2,
                "exit_condition": "Customer is satisfied, deal is progressing, or final answer delivered",
                "steps": [
                    {
                        "id": "sales_3_0_check",
                        "type": "decision",
                        "name": "Outcome Check",
                        "instruction": "Is the customer engaged? Are there unresolved objections? Should we pivot strategy?",
                        "exit_condition": "If customer is engaged → deliver. If not → refine approach.",
                    },
                ],
            },
            {
                "id": "sales_4_deliver",
                "type": "action",
                "name": "Deliver Sales Recommendation",
                "category": "output",
                "instruction": (
                    "Summarize the sales strategy and outcomes:\n"
                    "- Key value propositions presented\n"
                    "- Objections handled and how\n"
                    "- Recommended next steps\n"
                    "- Follow-up timeline\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Sales engagement complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # TECH SUPPORT ORCHESTRATOR (AIS-71)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Tech Support Expert",
        "description": "Orchestrator for technical support: problem diagnosis, troubleshooting, escalation, and resolution tracking",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "ts_0_diagnose",
                "type": "action",
                "name": "Diagnose Problem",
                "category": "analysis",
                "instruction": (
                    "Analyze the technical issue:\n"
                    "- What is the user experiencing? (symptoms, error messages)\n"
                    "- What system/product/service is affected?\n"
                    "- When did the issue start? Any recent changes?\n"
                    "- What has the user already tried?\n"
                    "- What is the severity/impact level?"
                ),
            },
            {
                "id": "ts_1_plan",
                "type": "todo",
                "name": "Create Troubleshooting Plan",
                "category": "planning",
                "instruction": (
                    "Build a troubleshooting strategy:\n"
                    "1. List most likely root causes (ordered by probability)\n"
                    "2. Define diagnostic checks for each cause\n"
                    "3. Plan step-by-step resolution attempts\n"
                    "4. Identify escalation criteria if basic troubleshooting fails\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "ts_2_resolve",
                "type": "action",
                "name": "Execute Resolution",
                "category": "execution",
                "instruction": (
                    "Walk through the troubleshooting steps:\n"
                    "- Try solutions starting from most likely cause\n"
                    "- Provide clear, step-by-step instructions\n"
                    "- Verify each step before moving to the next\n"
                    "- Document what works and what doesn't\n"
                    "- If applicable, use skills to check logs, run commands, etc."
                ),
            },
            {
                "id": "ts_3_evaluate",
                "type": "loop",
                "name": "Verify & Iterate",
                "category": "verification",
                "instruction": "Check if the issue is resolved and iterate if needed.",
                "max_iterations": 3,
                "exit_condition": "Issue resolved or escalation needed",
                "steps": [
                    {
                        "id": "ts_3_0_check",
                        "type": "decision",
                        "name": "Resolution Check",
                        "instruction": "Is the problem resolved? If not, try the next troubleshooting step. If all options exhausted, recommend escalation.",
                        "exit_condition": "If resolved → deliver. If not → next troubleshooting step.",
                    },
                ],
            },
            {
                "id": "ts_4_deliver",
                "type": "action",
                "name": "Deliver Resolution Summary",
                "category": "output",
                "instruction": (
                    "Summarize the support interaction:\n"
                    "- Problem description\n"
                    "- Root cause identified\n"
                    "- Steps taken to resolve\n"
                    "- Preventive recommendations\n"
                    "- Follow-up actions if needed\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Technical support complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # PROJECT MANAGER ORCHESTRATOR (AIS-77)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Project Manager Expert",
        "description": "Orchestrator for project management: planning, resource allocation, risk management, and delivery tracking",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "pm_0_assess",
                "type": "action",
                "name": "Assess Project Context",
                "category": "analysis",
                "instruction": (
                    "Understand the project landscape:\n"
                    "- What is the project scope and key objectives?\n"
                    "- What are the constraints (time, budget, resources)?\n"
                    "- Who are the stakeholders and their expectations?\n"
                    "- What risks and dependencies exist?\n"
                    "- What is the current project status (if ongoing)?"
                ),
            },
            {
                "id": "pm_1_plan",
                "type": "todo",
                "name": "Create Project Plan",
                "category": "planning",
                "instruction": (
                    "Build a comprehensive project plan:\n"
                    "1. Define milestones and deliverables\n"
                    "2. Break down work into manageable tasks\n"
                    "3. Estimate timelines and assign priorities\n"
                    "4. Identify resource needs\n"
                    "5. Create risk mitigation strategies\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "pm_2_execute",
                "type": "action",
                "name": "Manage Execution",
                "category": "execution",
                "instruction": (
                    "Coordinate project execution:\n"
                    "- Track progress against milestones\n"
                    "- Identify blockers and resolve them\n"
                    "- Adjust priorities and plans as needed\n"
                    "- Communicate status updates to stakeholders\n"
                    "- Manage scope changes through change control"
                ),
            },
            {
                "id": "pm_3_evaluate",
                "type": "loop",
                "name": "Monitor & Adjust",
                "category": "verification",
                "instruction": "Review project status and adjust the plan if needed.",
                "max_iterations": 3,
                "exit_condition": "Project deliverables are on track or plan is adjusted",
                "steps": [
                    {
                        "id": "pm_3_0_check",
                        "type": "decision",
                        "name": "Status Check",
                        "instruction": "Are we on track? Are there new risks? Should we re-prioritize? If yes → adjust plan. If all good → proceed to delivery.",
                        "exit_condition": "Project is on track → deliver status report.",
                    },
                ],
            },
            {
                "id": "pm_4_deliver",
                "type": "action",
                "name": "Deliver Project Summary",
                "category": "output",
                "instruction": (
                    "Provide a project management deliverable:\n"
                    "- Executive summary\n"
                    "- Current status vs plan\n"
                    "- Key risks and mitigations\n"
                    "- Action items and ownership\n"
                    "- Recommendations for next phase\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Project management complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # MARKETER ORCHESTRATOR (AIS-79)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Marketing Expert",
        "description": "Orchestrator for marketing strategy: market analysis, campaign planning, content strategy, and performance optimization",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "mkt_0_analyze",
                "type": "action",
                "name": "Analyze Market Context",
                "category": "analysis",
                "instruction": (
                    "Understand the marketing landscape:\n"
                    "- What product/service/brand are we marketing?\n"
                    "- Who is the target audience (demographics, psychographics, behavior)?\n"
                    "- What is the competitive positioning?\n"
                    "- What channels are available (digital, social, email, content, paid)?\n"
                    "- What is the marketing budget and timeline?"
                ),
            },
            {
                "id": "mkt_1_plan",
                "type": "todo",
                "name": "Create Marketing Strategy",
                "category": "planning",
                "instruction": (
                    "Build a marketing action plan:\n"
                    "1. Define marketing objectives and KPIs\n"
                    "2. Develop messaging and positioning strategy\n"
                    "3. Select channels and tactics\n"
                    "4. Plan content calendar and campaign timeline\n"
                    "5. Set budget allocation per channel\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "mkt_2_execute",
                "type": "action",
                "name": "Develop Campaign Assets",
                "category": "execution",
                "instruction": (
                    "Create marketing deliverables:\n"
                    "- Write copy for selected channels (ads, social posts, emails, landing pages)\n"
                    "- Develop content strategy and key messages\n"
                    "- Define A/B testing hypotheses\n"
                    "- Create performance tracking framework\n"
                    "- Plan customer journey touchpoints"
                ),
            },
            {
                "id": "mkt_3_evaluate",
                "type": "loop",
                "name": "Optimize & Iterate",
                "category": "verification",
                "instruction": "Review marketing strategy and optimize based on insights.",
                "max_iterations": 2,
                "exit_condition": "Marketing strategy is comprehensive and actionable",
                "steps": [
                    {
                        "id": "mkt_3_0_check",
                        "type": "decision",
                        "name": "Quality Check",
                        "instruction": "Is the strategy covering all key channels? Is messaging consistent? Are KPIs measurable? Refine if needed.",
                        "exit_condition": "Strategy is complete → deliver.",
                    },
                ],
            },
            {
                "id": "mkt_4_deliver",
                "type": "action",
                "name": "Deliver Marketing Plan",
                "category": "output",
                "instruction": (
                    "Compile the marketing deliverable:\n"
                    "- Marketing strategy overview\n"
                    "- Campaign assets and content\n"
                    "- Channel-specific tactics\n"
                    "- KPIs and measurement plan\n"
                    "- Timeline and budget breakdown\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Marketing strategy complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # PHYSICIST ORCHESTRATOR (AIS-80)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Physics Expert",
        "description": "Orchestrator for physics consulting: problem analysis, theoretical modeling, calculations, and experimental design",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "phys_0_analyze",
                "type": "action",
                "name": "Analyze Physics Problem",
                "category": "analysis",
                "instruction": (
                    "Understand the physics problem:\n"
                    "- What physical phenomenon or system is involved?\n"
                    "- What branch of physics applies (mechanics, thermodynamics, electrodynamics, quantum, optics, etc.)?\n"
                    "- What are the given parameters and constraints?\n"
                    "- What assumptions can reasonably be made?\n"
                    "- What level of rigor is needed (qualitative explanation vs precise calculation)?"
                ),
            },
            {
                "id": "phys_1_model",
                "type": "todo",
                "name": "Build Physical Model",
                "category": "planning",
                "instruction": (
                    "Construct the theoretical framework:\n"
                    "1. Identify relevant physical laws and equations\n"
                    "2. Define the system boundaries and state variables\n"
                    "3. List assumptions and their validity ranges\n"
                    "4. Plan the calculation approach (analytical, numerical, dimensional analysis)\n"
                    "5. Identify what experimental data is needed (if any)\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "phys_2_solve",
                "type": "action",
                "name": "Solve & Calculate",
                "category": "execution",
                "instruction": (
                    "Execute the physics solution:\n"
                    "- Apply the selected equations and methods\n"
                    "- Show derivations step-by-step\n"
                    "- Perform numerical calculations with units\n"
                    "- Check dimensional consistency\n"
                    "- Verify results against limiting cases and physical intuition"
                ),
            },
            {
                "id": "phys_3_evaluate",
                "type": "loop",
                "name": "Verify & Refine",
                "category": "verification",
                "instruction": "Verify the solution for correctness and physical plausibility.",
                "max_iterations": 2,
                "exit_condition": "Solution is verified and physically consistent",
                "steps": [
                    {
                        "id": "phys_3_0_check",
                        "type": "decision",
                        "name": "Sanity Check",
                        "instruction": "Do the results make physical sense? Are units correct? Do limiting cases work? If issues found → refine the model.",
                        "exit_condition": "Results are physically plausible → deliver.",
                    },
                ],
            },
            {
                "id": "phys_4_deliver",
                "type": "action",
                "name": "Deliver Physics Analysis",
                "category": "output",
                "instruction": (
                    "Present the physics analysis:\n"
                    "- Problem statement and assumptions\n"
                    "- Theoretical framework used\n"
                    "- Step-by-step solution with explanations\n"
                    "- Numerical results with units\n"
                    "- Physical interpretation and implications\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Physics analysis complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # CHEMIST ORCHESTRATOR (AIS-81)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Chemistry Expert",
        "description": "Orchestrator for chemistry consulting: reaction analysis, molecular design, safety assessment, and lab procedures",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "chem_0_analyze",
                "type": "action",
                "name": "Analyze Chemistry Problem",
                "category": "analysis",
                "instruction": (
                    "Understand the chemistry problem:\n"
                    "- What chemical system or reaction is involved?\n"
                    "- What branch applies (organic, inorganic, physical, analytical, biochemistry)?\n"
                    "- What substances, concentrations, and conditions are given?\n"
                    "- What is the desired outcome (synthesis, analysis, explanation)?\n"
                    "- Are there safety considerations?"
                ),
            },
            {
                "id": "chem_1_plan",
                "type": "todo",
                "name": "Plan Chemical Approach",
                "category": "planning",
                "instruction": (
                    "Build the chemistry strategy:\n"
                    "1. Identify relevant reactions and mechanisms\n"
                    "2. Consider thermodynamic and kinetic factors\n"
                    "3. Plan synthesis routes or analytical methods\n"
                    "4. Assess safety and environmental considerations\n"
                    "5. Identify required reagents, equipment, and conditions\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "chem_2_solve",
                "type": "action",
                "name": "Execute Chemical Analysis",
                "category": "execution",
                "instruction": (
                    "Perform the chemistry work:\n"
                    "- Write balanced equations with mechanisms if needed\n"
                    "- Calculate stoichiometry, yields, and concentrations\n"
                    "- Design or explain synthetic routes\n"
                    "- Predict products and byproducts\n"
                    "- Consider reaction conditions (temperature, pressure, catalysts, solvents)"
                ),
            },
            {
                "id": "chem_3_evaluate",
                "type": "loop",
                "name": "Verify & Refine",
                "category": "verification",
                "instruction": "Check the chemical solution for correctness and practicality.",
                "max_iterations": 2,
                "exit_condition": "Solution is chemically sound and practical",
                "steps": [
                    {
                        "id": "chem_3_0_check",
                        "type": "decision",
                        "name": "Validation Check",
                        "instruction": "Are the equations balanced? Are conditions realistic? Are safety hazards addressed? If issues → refine.",
                        "exit_condition": "Chemistry is correct and practical → deliver.",
                    },
                ],
            },
            {
                "id": "chem_4_deliver",
                "type": "action",
                "name": "Deliver Chemistry Analysis",
                "category": "output",
                "instruction": (
                    "Present the chemistry analysis:\n"
                    "- Problem statement and context\n"
                    "- Reaction equations and mechanisms\n"
                    "- Calculations and predicted results\n"
                    "- Safety notes and handling precautions\n"
                    "- Practical recommendations\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Chemistry analysis complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # ENGINEER ORCHESTRATOR (AIS-82)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Engineering Expert",
        "description": "Orchestrator for engineering consulting: design analysis, feasibility studies, technical calculations, and system optimization",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "eng_0_analyze",
                "type": "action",
                "name": "Analyze Engineering Challenge",
                "category": "analysis",
                "instruction": (
                    "Understand the engineering problem:\n"
                    "- What engineering discipline applies (mechanical, electrical, civil, aerospace, etc.)?\n"
                    "- What are the design requirements and specifications?\n"
                    "- What are the constraints (material, cost, weight, power, environment)?\n"
                    "- What standards and regulations apply?\n"
                    "- What is the current state of the system (existing design, failure analysis)?"
                ),
            },
            {
                "id": "eng_1_design",
                "type": "todo",
                "name": "Create Engineering Design",
                "category": "planning",
                "instruction": (
                    "Build the engineering approach:\n"
                    "1. Define functional requirements and performance criteria\n"
                    "2. Propose design concepts and trade-off analysis\n"
                    "3. Plan calculations and simulations needed\n"
                    "4. Identify materials and components\n"
                    "5. Create verification and validation plan\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "eng_2_calculate",
                "type": "action",
                "name": "Execute Engineering Analysis",
                "category": "execution",
                "instruction": (
                    "Perform engineering calculations and analysis:\n"
                    "- Apply relevant engineering formulas and standards\n"
                    "- Perform sizing, stress, thermal, or electrical calculations\n"
                    "- Evaluate safety factors and margins\n"
                    "- Optimize design parameters\n"
                    "- Create specifications and design documentation"
                ),
            },
            {
                "id": "eng_3_evaluate",
                "type": "loop",
                "name": "Review & Optimize",
                "category": "verification",
                "instruction": "Verify the engineering solution meets all requirements.",
                "max_iterations": 2,
                "exit_condition": "Design meets requirements with adequate safety margins",
                "steps": [
                    {
                        "id": "eng_3_0_check",
                        "type": "decision",
                        "name": "Design Review",
                        "instruction": "Does the design meet all specs? Are safety margins adequate? Are there manufacturing concerns? If issues → iterate on design.",
                        "exit_condition": "Design passes review → deliver.",
                    },
                ],
            },
            {
                "id": "eng_4_deliver",
                "type": "action",
                "name": "Deliver Engineering Solution",
                "category": "output",
                "instruction": (
                    "Present the engineering deliverable:\n"
                    "- Design overview and specifications\n"
                    "- Calculations and analysis results\n"
                    "- Material and component selections\n"
                    "- Safety factors and compliance notes\n"
                    "- Recommendations and next steps\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Engineering analysis complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # INVENTOR ORCHESTRATOR (AIS-83)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Inventor Expert",
        "description": "Orchestrator for invention and innovation: ideation, feasibility analysis, prototyping strategy, and patent considerations",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "inv_0_analyze",
                "type": "action",
                "name": "Understand the Challenge",
                "category": "analysis",
                "instruction": (
                    "Deeply understand the problem to solve:\n"
                    "- What is the core problem or unmet need?\n"
                    "- Who experiences this problem and in what context?\n"
                    "- What existing solutions exist and why are they insufficient?\n"
                    "- What are the key constraints (physics, cost, technology, regulations)?\n"
                    "- What would an ideal solution look like?"
                ),
            },
            {
                "id": "inv_1_ideate",
                "type": "todo",
                "name": "Generate & Evaluate Ideas",
                "category": "planning",
                "instruction": (
                    "Creative ideation phase:\n"
                    "1. Generate multiple solution concepts (aim for 5+ diverse approaches)\n"
                    "2. Use lateral thinking, biomimicry, TRIZ, or first-principles reasoning\n"
                    "3. Evaluate each concept against criteria (feasibility, novelty, impact)\n"
                    "4. Select the most promising concept(s) for development\n"
                    "5. Identify what needs to be proven or tested\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "inv_2_develop",
                "type": "action",
                "name": "Develop the Invention",
                "category": "execution",
                "instruction": (
                    "Flesh out the selected concept:\n"
                    "- Define how the invention works in detail\n"
                    "- Identify key technical challenges and how to address them\n"
                    "- Propose a proof-of-concept or prototype approach\n"
                    "- Consider manufacturing/production feasibility\n"
                    "- Assess patentability and prior art briefly"
                ),
            },
            {
                "id": "inv_3_evaluate",
                "type": "loop",
                "name": "Refine & Validate",
                "category": "verification",
                "instruction": "Stress-test the invention concept and refine it.",
                "max_iterations": 2,
                "exit_condition": "Invention concept is robust and well-defined",
                "steps": [
                    {
                        "id": "inv_3_0_check",
                        "type": "decision",
                        "name": "Feasibility Check",
                        "instruction": "Does the invention work in theory? Are there fatal flaws? Is it novel? If concerns → iterate on the concept.",
                        "exit_condition": "Concept is solid → deliver.",
                    },
                ],
            },
            {
                "id": "inv_4_deliver",
                "type": "action",
                "name": "Deliver Invention Brief",
                "category": "output",
                "instruction": (
                    "Present the invention:\n"
                    "- Problem statement\n"
                    "- Invention description and how it works\n"
                    "- Key innovations and advantages\n"
                    "- Technical challenges and mitigations\n"
                    "- Prototype/next steps roadmap\n"
                    "- Patent considerations\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Invention brief complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # LAWYER ORCHESTRATOR (AIS-84)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Legal Expert",
        "description": "Orchestrator for legal consulting: legal analysis, risk assessment, contract review, and compliance guidance",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "law_0_analyze",
                "type": "action",
                "name": "Analyze Legal Situation",
                "category": "analysis",
                "instruction": (
                    "Understand the legal question:\n"
                    "- What area of law applies (contract, corporate, IP, employment, regulatory, etc.)?\n"
                    "- What jurisdiction is relevant?\n"
                    "- What are the key facts and circumstances?\n"
                    "- Who are the parties involved and their interests?\n"
                    "- What is the desired legal outcome?\n"
                    "DISCLAIMER: Always note that this is informational analysis, not legal advice."
                ),
            },
            {
                "id": "law_1_research",
                "type": "todo",
                "name": "Legal Research & Framework",
                "category": "planning",
                "instruction": (
                    "Build the legal analysis framework:\n"
                    "1. Identify applicable laws, regulations, and precedents\n"
                    "2. Analyze how the law applies to the specific facts\n"
                    "3. Identify legal risks and exposure\n"
                    "4. Consider counter-arguments and opposing positions\n"
                    "5. Develop strategic recommendations\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "law_2_analyze",
                "type": "action",
                "name": "Perform Legal Analysis",
                "category": "execution",
                "instruction": (
                    "Execute the legal analysis:\n"
                    "- Apply relevant legal principles to the facts\n"
                    "- Assess strengths and weaknesses of each position\n"
                    "- Review contracts or documents if applicable\n"
                    "- Identify compliance gaps or risks\n"
                    "- Propose risk mitigation strategies"
                ),
            },
            {
                "id": "law_3_evaluate",
                "type": "loop",
                "name": "Review & Strengthen",
                "category": "verification",
                "instruction": "Review the legal analysis for completeness and accuracy.",
                "max_iterations": 2,
                "exit_condition": "Legal analysis is comprehensive and balanced",
                "steps": [
                    {
                        "id": "law_3_0_check",
                        "type": "decision",
                        "name": "Analysis Review",
                        "instruction": "Have all relevant legal areas been covered? Are risks properly identified? Is the advice balanced? If gaps → supplement analysis.",
                        "exit_condition": "Analysis is complete → deliver.",
                    },
                ],
            },
            {
                "id": "law_4_deliver",
                "type": "action",
                "name": "Deliver Legal Opinion",
                "category": "output",
                "instruction": (
                    "Present the legal analysis:\n"
                    "- Issue summary\n"
                    "- Applicable legal framework\n"
                    "- Analysis and conclusions\n"
                    "- Risk assessment (high/medium/low)\n"
                    "- Recommended actions\n"
                    "- DISCLAIMER: This is an AI analysis, not professional legal advice\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Legal analysis complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # PSYCHOLOGIST ORCHESTRATOR (AIS-86)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Psychology Expert",
        "description": "Orchestrator for psychology consulting: behavioral analysis, cognitive patterns, emotional intelligence, and well-being strategies",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "psy_0_assess",
                "type": "action",
                "name": "Assess Psychological Context",
                "category": "analysis",
                "instruction": (
                    "Understand the psychological question:\n"
                    "- What domain applies (cognitive, behavioral, social, developmental, organizational, etc.)?\n"
                    "- What is the specific issue or question?\n"
                    "- What is the context (personal development, team dynamics, decision-making, etc.)?\n"
                    "- What patterns or behaviors are being observed?\n"
                    "- DISCLAIMER: Note that this is educational/informational, not therapy or clinical diagnosis."
                ),
            },
            {
                "id": "psy_1_framework",
                "type": "todo",
                "name": "Build Psychological Framework",
                "category": "planning",
                "instruction": (
                    "Develop the psychological approach:\n"
                    "1. Identify relevant psychological theories and models\n"
                    "2. Analyze the situation through appropriate lenses (CBT, behavioral, humanistic, etc.)\n"
                    "3. Consider contributing factors (cognitive biases, environmental, social)\n"
                    "4. Plan evidence-based recommendations\n"
                    "5. Design actionable strategies for change\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "psy_2_analyze",
                "type": "action",
                "name": "Provide Psychological Analysis",
                "category": "execution",
                "instruction": (
                    "Apply psychological knowledge:\n"
                    "- Explain relevant psychological mechanisms\n"
                    "- Identify cognitive patterns and biases at play\n"
                    "- Offer evidence-based insights\n"
                    "- Suggest practical strategies and techniques\n"
                    "- Consider cultural and individual differences"
                ),
            },
            {
                "id": "psy_3_evaluate",
                "type": "loop",
                "name": "Refine & Validate",
                "category": "verification",
                "instruction": "Review the psychological analysis for depth and practical applicability.",
                "max_iterations": 2,
                "exit_condition": "Analysis is thorough and recommendations are actionable",
                "steps": [
                    {
                        "id": "psy_3_0_check",
                        "type": "decision",
                        "name": "Quality Check",
                        "instruction": "Is the analysis grounded in evidence? Are recommendations practical? Is it empathetic and non-judgmental? If not → refine.",
                        "exit_condition": "Analysis is solid → deliver.",
                    },
                ],
            },
            {
                "id": "psy_4_deliver",
                "type": "action",
                "name": "Deliver Psychological Insights",
                "category": "output",
                "instruction": (
                    "Present the psychological analysis:\n"
                    "- Understanding of the situation\n"
                    "- Relevant psychological principles\n"
                    "- Key insights and patterns identified\n"
                    "- Practical strategies and action steps\n"
                    "- Resources for further exploration\n"
                    "- DISCLAIMER: This is educational, not clinical advice\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Psychological analysis complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # GYM TRAINER ORCHESTRATOR (AIS-88)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Fitness Trainer Expert",
        "description": "Orchestrator for fitness consulting: training program design, nutrition guidance, injury prevention, and progress tracking",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "fit_0_assess",
                "type": "action",
                "name": "Assess Fitness Profile",
                "category": "analysis",
                "instruction": (
                    "Understand the fitness context:\n"
                    "- What are the fitness goals (strength, muscle gain, weight loss, endurance, flexibility)?\n"
                    "- What is the current fitness level and experience?\n"
                    "- Are there any injuries, limitations, or medical conditions?\n"
                    "- What equipment/gym access is available?\n"
                    "- How much time per week can be dedicated to training?\n"
                    "DISCLAIMER: Note that this is general fitness guidance, not medical advice."
                ),
            },
            {
                "id": "fit_1_program",
                "type": "todo",
                "name": "Design Training Program",
                "category": "planning",
                "instruction": (
                    "Build a personalized training program:\n"
                    "1. Set realistic short-term and long-term goals\n"
                    "2. Design weekly training split (muscle groups, rest days)\n"
                    "3. Select exercises with sets, reps, and rest periods\n"
                    "4. Plan progressive overload strategy\n"
                    "5. Include warm-up and mobility work\n"
                    "6. Outline basic nutrition guidelines\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "fit_2_detail",
                "type": "action",
                "name": "Detail Workout Plan",
                "category": "execution",
                "instruction": (
                    "Flesh out the training program:\n"
                    "- Write out each workout day with specific exercises\n"
                    "- Include proper form cues and common mistakes\n"
                    "- Add progression targets for each week\n"
                    "- Provide alternative exercises for equipment limitations\n"
                    "- Include stretching and recovery recommendations"
                ),
            },
            {
                "id": "fit_3_evaluate",
                "type": "loop",
                "name": "Review & Adjust",
                "category": "verification",
                "instruction": "Review the program for balance and safety.",
                "max_iterations": 2,
                "exit_condition": "Program is balanced, safe, and aligned with goals",
                "steps": [
                    {
                        "id": "fit_3_0_check",
                        "type": "decision",
                        "name": "Program Review",
                        "instruction": "Is volume appropriate for the experience level? Are muscle groups balanced? Is recovery adequate? If not → adjust program.",
                        "exit_condition": "Program is balanced → deliver.",
                    },
                ],
            },
            {
                "id": "fit_4_deliver",
                "type": "action",
                "name": "Deliver Fitness Plan",
                "category": "output",
                "instruction": (
                    "Present the fitness plan:\n"
                    "- Goals and timeline\n"
                    "- Weekly training schedule\n"
                    "- Detailed workouts with exercises, sets, reps\n"
                    "- Nutrition guidelines\n"
                    "- Progress tracking recommendations\n"
                    "- DISCLAIMER: Consult a doctor before starting a new program\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Fitness plan complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # MEDIC ORCHESTRATOR (AIS-89)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Medical Expert",
        "description": "Orchestrator for medical consulting: symptom analysis, health information, prevention strategies, and wellness guidance",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "med_0_assess",
                "type": "action",
                "name": "Assess Health Context",
                "category": "analysis",
                "instruction": (
                    "Understand the health question:\n"
                    "- What symptoms or health concerns are described?\n"
                    "- What is the patient's general health context?\n"
                    "- What is the timeline and severity?\n"
                    "- What medications or treatments are currently used?\n"
                    "- Are there risk factors (age, conditions, family history)?\n"
                    "CRITICAL DISCLAIMER: This is educational health information only. It is NOT a diagnosis or treatment plan. Always advise consulting a qualified healthcare professional."
                ),
            },
            {
                "id": "med_1_research",
                "type": "todo",
                "name": "Research Health Topic",
                "category": "planning",
                "instruction": (
                    "Build the medical information framework:\n"
                    "1. Identify potentially relevant conditions or mechanisms\n"
                    "2. Review evidence-based information on the topic\n"
                    "3. Consider differential factors that a doctor would explore\n"
                    "4. Identify when to seek emergency care vs routine care\n"
                    "5. Prepare prevention and wellness recommendations\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "med_2_inform",
                "type": "action",
                "name": "Provide Health Information",
                "category": "execution",
                "instruction": (
                    "Share evidence-based health information:\n"
                    "- Explain relevant medical concepts in accessible language\n"
                    "- Describe what symptoms might indicate (without diagnosing)\n"
                    "- Outline general prevention and wellness strategies\n"
                    "- Highlight red flags that warrant immediate medical attention\n"
                    "- Suggest questions to ask a healthcare provider"
                ),
            },
            {
                "id": "med_3_evaluate",
                "type": "loop",
                "name": "Review & Validate",
                "category": "verification",
                "instruction": "Ensure information is accurate, balanced, and safe.",
                "max_iterations": 2,
                "exit_condition": "Information is accurate and appropriately caveated",
                "steps": [
                    {
                        "id": "med_3_0_check",
                        "type": "decision",
                        "name": "Safety Check",
                        "instruction": "Is the information evidence-based? Are disclaimers present? Does it avoid making diagnoses? Are emergency signs mentioned if relevant? If not → improve.",
                        "exit_condition": "Information is safe and accurate → deliver.",
                    },
                ],
            },
            {
                "id": "med_4_deliver",
                "type": "action",
                "name": "Deliver Health Information",
                "category": "output",
                "instruction": (
                    "Present the health information:\n"
                    "- Topic overview\n"
                    "- Evidence-based explanations\n"
                    "- Prevention and wellness tips\n"
                    "- When to see a doctor (red flags)\n"
                    "- Questions to ask your healthcare provider\n"
                    "- CRITICAL DISCLAIMER: This is NOT medical advice. Consult a healthcare professional.\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Health information complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # VETERINARIAN ORCHESTRATOR (AIS-90)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Veterinary Expert",
        "description": "Orchestrator for veterinary consulting: animal health assessment, care guidance, nutrition, and behavior analysis",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "vet_0_assess",
                "type": "action",
                "name": "Assess Animal Health Context",
                "category": "analysis",
                "instruction": (
                    "Understand the veterinary question:\n"
                    "- What animal species and breed is involved?\n"
                    "- What symptoms or concerns are described?\n"
                    "- What is the animal's age, weight, and health history?\n"
                    "- What is the environment (indoor/outdoor, diet, exercise)?\n"
                    "- What urgency level (emergency vs routine care)?\n"
                    "DISCLAIMER: This is general pet health information. Always consult a licensed veterinarian for proper diagnosis and treatment."
                ),
            },
            {
                "id": "vet_1_research",
                "type": "todo",
                "name": "Research Veterinary Topic",
                "category": "planning",
                "instruction": (
                    "Build the veterinary knowledge framework:\n"
                    "1. Identify common conditions matching the description\n"
                    "2. Consider species-specific factors\n"
                    "3. Review standard veterinary care practices\n"
                    "4. Identify emergency signs requiring immediate vet visit\n"
                    "5. Prepare care and prevention recommendations\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "vet_2_advise",
                "type": "action",
                "name": "Provide Veterinary Guidance",
                "category": "execution",
                "instruction": (
                    "Share veterinary care information:\n"
                    "- Explain possible causes and what they mean\n"
                    "- Provide first-aid or home care tips (if safe)\n"
                    "- Recommend nutrition and lifestyle adjustments\n"
                    "- Explain what a vet would likely do (tests, treatments)\n"
                    "- Highlight emergency indicators requiring immediate vet visit"
                ),
            },
            {
                "id": "vet_3_evaluate",
                "type": "loop",
                "name": "Review & Validate",
                "category": "verification",
                "instruction": "Ensure advice is safe and species-appropriate.",
                "max_iterations": 2,
                "exit_condition": "Guidance is safe, species-appropriate, and well-caveated",
                "steps": [
                    {
                        "id": "vet_3_0_check",
                        "type": "decision",
                        "name": "Safety Check",
                        "instruction": "Is the advice safe for the specific species? Are disclaimers present? Are emergency signs mentioned? If issues → refine.",
                        "exit_condition": "Guidance is safe → deliver.",
                    },
                ],
            },
            {
                "id": "vet_4_deliver",
                "type": "action",
                "name": "Deliver Veterinary Advice",
                "category": "output",
                "instruction": (
                    "Present veterinary guidance:\n"
                    "- Animal profile and concern summary\n"
                    "- Possible explanations (without diagnosing)\n"
                    "- Home care and prevention tips\n"
                    "- When to visit the vet (red flags)\n"
                    "- Questions to ask your veterinarian\n"
                    "- DISCLAIMER: Consult a licensed veterinarian for proper care\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Veterinary guidance complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # PRODUCER ORCHESTRATOR (AIS-91)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Producer Expert",
        "description": "Orchestrator for content/media production: concept development, production planning, creative direction, and launch strategy",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "prod_0_analyze",
                "type": "action",
                "name": "Analyze Production Brief",
                "category": "analysis",
                "instruction": (
                    "Understand the production context:\n"
                    "- What type of production (video, audio, event, digital content, music, film)?\n"
                    "- What is the creative vision and target audience?\n"
                    "- What are the budget and resource constraints?\n"
                    "- What is the timeline and key milestones?\n"
                    "- What platforms/channels will be used for distribution?"
                ),
            },
            {
                "id": "prod_1_plan",
                "type": "todo",
                "name": "Create Production Plan",
                "category": "planning",
                "instruction": (
                    "Build a comprehensive production plan:\n"
                    "1. Define creative concept and narrative structure\n"
                    "2. Break down into pre-production, production, and post-production phases\n"
                    "3. Identify required talent, equipment, and locations\n"
                    "4. Create production schedule with milestones\n"
                    "5. Plan distribution and promotion strategy\n"
                    "6. Budget allocation across phases\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "prod_2_develop",
                "type": "action",
                "name": "Develop Production Assets",
                "category": "execution",
                "instruction": (
                    "Create production deliverables:\n"
                    "- Write scripts, outlines, or storyboards\n"
                    "- Plan shot lists or content schedules\n"
                    "- Define creative direction (style, tone, mood)\n"
                    "- Develop brand guidelines or creative briefs\n"
                    "- Create distribution and marketing strategy"
                ),
            },
            {
                "id": "prod_3_evaluate",
                "type": "loop",
                "name": "Review & Polish",
                "category": "verification",
                "instruction": "Review production plan for quality and feasibility.",
                "max_iterations": 2,
                "exit_condition": "Production plan is comprehensive and achievable",
                "steps": [
                    {
                        "id": "prod_3_0_check",
                        "type": "decision",
                        "name": "Production Review",
                        "instruction": "Is the creative vision clear? Is the timeline realistic? Is the budget covered? Are all phases planned? If gaps → refine.",
                        "exit_condition": "Plan is complete → deliver.",
                    },
                ],
            },
            {
                "id": "prod_4_deliver",
                "type": "action",
                "name": "Deliver Production Package",
                "category": "output",
                "instruction": (
                    "Present the production package:\n"
                    "- Creative concept and vision\n"
                    "- Production timeline and milestones\n"
                    "- Scripts, outlines, or storyboards\n"
                    "- Resource and budget breakdown\n"
                    "- Distribution and marketing plan\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Production plan complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # ACCOUNTANT ORCHESTRATOR (AIS-85)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "Accountant Expert",
        "description": "Orchestrator for accounting and finance: bookkeeping analysis, tax planning, financial reporting, compliance, and budgeting",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "acct_0_assess",
                "type": "action",
                "name": "Assess Financial Situation",
                "category": "analysis",
                "instruction": (
                    "Analyze the financial/accounting context:\n"
                    "- What is the entity type (individual, LLC, corporation, non-profit)?\n"
                    "- What is the accounting question (bookkeeping, taxes, reporting, compliance, budgeting)?\n"
                    "- What jurisdiction and tax regime applies?\n"
                    "- What accounting standards are relevant (GAAP, IFRS, local statutory)?\n"
                    "- What is the fiscal period and any upcoming deadlines?\n"
                    "- What financial data or documents are available?"
                ),
            },
            {
                "id": "acct_1_plan",
                "type": "todo",
                "name": "Create Accounting Plan",
                "category": "planning",
                "instruction": (
                    "Build an accounting action plan:\n"
                    "1. Identify applicable accounting standards and regulations\n"
                    "2. Determine required financial statements or reports\n"
                    "3. List journal entries, adjustments, or calculations needed\n"
                    "4. Plan tax implications and optimization strategies\n"
                    "5. Identify compliance requirements and deadlines\n"
                    "6. Outline verification and reconciliation steps\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "acct_2_execute",
                "type": "action",
                "name": "Perform Accounting Work",
                "category": "execution",
                "instruction": (
                    "Execute the accounting tasks:\n"
                    "- Prepare journal entries with proper debit/credit classification\n"
                    "- Calculate tax liabilities, deductions, and credits\n"
                    "- Build financial statements (income statement, balance sheet, cash flow)\n"
                    "- Perform ratio analysis and financial health assessment\n"
                    "- Draft budget forecasts or variance analysis\n"
                    "- Document assumptions and accounting policies applied"
                ),
            },
            {
                "id": "acct_3_verify",
                "type": "loop",
                "name": "Verify & Reconcile",
                "category": "verification",
                "instruction": "Review accounting work for accuracy, compliance, and completeness.",
                "max_iterations": 2,
                "exit_condition": "All figures reconcile, standards are met, and compliance is verified",
                "steps": [
                    {
                        "id": "acct_3_0_check",
                        "type": "decision",
                        "name": "Accuracy Check",
                        "instruction": "Do debits equal credits? Do totals reconcile? Are tax calculations correct? Are all regulatory requirements addressed? If discrepancies → fix.",
                        "exit_condition": "All reconciled and compliant → deliver.",
                    },
                ],
            },
            {
                "id": "acct_4_deliver",
                "type": "action",
                "name": "Deliver Financial Report",
                "category": "output",
                "instruction": (
                    "Present the accounting deliverables:\n"
                    "- Financial statements or reports with clear formatting\n"
                    "- Tax calculations with supporting schedules\n"
                    "- Key findings, risks, and recommendations\n"
                    "- Compliance status and upcoming deadlines\n"
                    "- Assumptions, limitations, and professional caveats\n\n"
                    "Signal completion: <<<DELEGATE_DONE:Accounting analysis complete>>>"
                ),
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # HR ORCHESTRATOR (AIS-78)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "HR Expert",
        "description": "Orchestrator for human resources: recruitment, employee relations, policies, compensation, training, and organizational development",
        "type": "orchestrator",
        "is_default": False,
        "steps": [
            {
                "id": "hr_0_assess",
                "type": "action",
                "name": "Assess HR Situation",
                "category": "analysis",
                "instruction": (
                    "Analyze the HR context:\n"
                    "- What area of HR is involved (recruitment, onboarding, performance, compensation, policies, training, offboarding)?\n"
                    "- What is the organizational context (company size, industry, culture)?\n"
                    "- What are the applicable labor laws and regulations?\n"
                    "- What is the current team structure and headcount?\n"
                    "- Are there any urgent issues (conflict, compliance risk, turnover)?\n"
                    "- What HR systems, processes, or policies already exist?"
                ),
            },
            {
                "id": "hr_1_plan",
                "type": "todo",
                "name": "Create HR Action Plan",
                "category": "planning",
                "instruction": (
                    "Build an HR action plan:\n"
                    "1. Identify applicable labor laws and compliance requirements\n"
                    "2. Define success criteria and KPIs for the HR initiative\n"
                    "3. Outline process steps (recruitment funnel, policy rollout, training program, etc.)\n"
                    "4. Identify stakeholders and approval processes\n"
                    "5. Plan timeline and resource allocation\n"
                    "6. Prepare risk mitigation for legal or cultural issues\n"
                    "Create a structured todo list for tracking."
                ),
            },
            {
                "id": "hr_2_execute",
                "type": "action",
                "name": "Develop HR Deliverables",
                "category": "execution",
                "instruction": (
                    "Execute the HR work:\n"
                    "- Draft job descriptions, interview guides, or evaluation rubrics\n"
                    "- Create or update HR policies and employee handbooks\n"
                    "- Design compensation and benefits packages\n"
                    "- Build training programs or development plans\n"
                    "- Draft employee communications or performance review templates\n"
                    "- Prepare onboarding/offboarding checklists"
                ),
            },
            {
                "id": "hr_3_review",
                "type": "loop",
                "name": "Review & Compliance Check",
                "category": "verification",
                "instruction": "Review HR deliverables for legal compliance, fairness, and organizational fit.",
                "max_iterations": 2,
                "exit_condition": "Deliverables are legally compliant, fair, and aligned with organizational values",
                "steps": [
                    {
                        "id": "hr_3_0_check",
                        "type": "decision",
                        "name": "Compliance & Fairness Check",
                        "instruction": "Are all deliverables legally compliant? Are policies fair and nondiscriminatory? Do they align with company culture and values? Are there potential liabilities? If issues → revise.",
                        "exit_condition": "All compliant and aligned → deliver.",
                    },
                ],
            },
            {
                "id": "hr_4_deliver",
                "type": "action",
                "name": "Deliver HR Package",
                "category": "output",
                "instruction": (
                    "Present the HR deliverables:\n"
                    "- Policies, documents, or templates ready for implementation\n"
                    "- Compliance notes and legal considerations\n"
                    "- Implementation timeline and rollout plan\n"
                    "- Key metrics to track success\n"
                    "- Recommendations for ongoing HR management\n\n"
                    "Signal completion: <<<DELEGATE_DONE:HR deliverables complete>>>"
                ),
            },
        ],
    },
]


async def create_default_protocols(db: AsyncIOMotorDatabase):
    """Create default thinking protocols if they don't exist.
    Also adds any new default protocols that were added after initial setup.
    """
    svc = ThinkingProtocolService(db)
    count = await svc.count()

    if count > 0:
        # Existing installation — check for missing default protocols and add them
        await _ensure_new_default_protocols(db)
        return

    # First-time setup: create all protocols
    proto_map = {}  # name -> MongoThinkingProtocol instance
    for proto_data in DEFAULT_PROTOCOLS:
        proto = MongoThinkingProtocol(
            name=proto_data["name"],
            description=proto_data["description"],
            type=proto_data.get("type", "standard"),
            steps=proto_data["steps"],
            is_default=proto_data.get("is_default", False),
        )
        proto = await svc.create(proto)
        proto_map[proto_data["name"]] = proto

    # Second pass: wire orchestrator delegate steps to actual protocol IDs
    # Collect IDs by category
    all_standard_ids = [str(p.id) for name, p in proto_map.items() if p.type == "standard"]
    programmer_id = str(proto_map["Programmer"].id) if "Programmer" in proto_map else None
    tester_id = str(proto_map["Tester"].id) if "Tester" in proto_map else None
    reviewer_id = str(proto_map["Code Reviewer"].id) if "Code Reviewer" in proto_map else None

    # Wire Development Orchestrator → Programmer, Tester, Code Reviewer
    dev_orch = proto_map.get("Development Orchestrator")
    if dev_orch:
        dev_child_ids = [pid for pid in [programmer_id, tester_id, reviewer_id] if pid]
        steps = list(dev_orch.steps)
        for step in steps:
            if step.get("type") == "delegate":
                step_name = step.get("name", "")
                if "Implement" in step_name and programmer_id:
                    step["protocol_ids"] = [programmer_id]
                elif "Test" in step_name and tester_id:
                    step["protocol_ids"] = [tester_id]
                elif "Review" in step_name and reviewer_id:
                    step["protocol_ids"] = [reviewer_id]
                else:
                    step["protocol_ids"] = dev_child_ids
        await svc.update(dev_orch.id, {"steps": steps})

    # Wire Master Orchestrator → ALL protocols (both standard and mid-level orchestrators)
    master = proto_map.get("Master Orchestrator")
    if master:
        all_ids = [str(p.id) for name, p in proto_map.items() if name != "Master Orchestrator"]
        steps = list(master.steps)
        for step in steps:
            if step.get("type") == "delegate":
                step["protocol_ids"] = all_ids
        await svc.update(master.id, {"steps": steps})

    # Keep backward compat: wire the old Adaptive Orchestrator too (if present)
    adaptive = proto_map.get("Adaptive Orchestrator")
    if adaptive:
        steps = list(adaptive.steps)
        for step in steps:
            if step.get("type") == "delegate":
                step["protocol_ids"] = all_standard_ids
        await svc.update(adaptive.id, {"steps": steps})


async def _ensure_new_default_protocols(db: AsyncIOMotorDatabase):
    """Add any default protocols that are missing from an existing installation.
    This allows new protocol templates to be auto-created on server restart
    without overwriting user-modified protocols.
    """
    svc = ThinkingProtocolService(db)
    existing = await svc.get_all(limit=500)
    existing_names = {p.name for p in existing}

    created = []
    for proto_data in DEFAULT_PROTOCOLS:
        if proto_data["name"] not in existing_names:
            proto = MongoThinkingProtocol(
                name=proto_data["name"],
                description=proto_data["description"],
                type=proto_data.get("type", "standard"),
                steps=proto_data["steps"],
                is_default=proto_data.get("is_default", False),
            )
            proto = await svc.create(proto)
            created.append(proto)

    if created:
        names = ", ".join(p.name for p in created)
        print(f"[PROTOCOLS] Added {len(created)} new default protocol(s): {names}")

        # Wire new protocols into existing orchestrators' delegate steps
        all_protos = await svc.get_all(limit=500)
        all_non_master_ids = [str(p.id) for p in all_protos if p.name != "Master Orchestrator"]

        master = next((p for p in all_protos if p.name == "Master Orchestrator"), None)
        if master:
            steps = list(master.steps)
            for step in steps:
                if step.get("type") == "delegate":
                    step["protocol_ids"] = all_non_master_ids
            await svc.update(master.id, {"steps": steps})


async def deduplicate_protocols(db: AsyncIOMotorDatabase):
    """
    Remove duplicate ThinkingProtocol records (same name + type).
    Keeps the protocol created first; deletes the rest.
    Re-points orphaned agent_protocols to the surviving record.
    """
    svc = ThinkingProtocolService(db)
    ap_svc = AgentProtocolService(db)

    # Find duplicate groups using aggregation pipeline
    pipeline = [
        {"$group": {"_id": {"name": "$name", "type": "$type"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
    ]
    cursor = svc.collection.aggregate(pipeline)
    dup_groups = await cursor.to_list(length=500)
    if not dup_groups:
        return 0

    removed = 0
    for group in dup_groups:
        name = group["_id"]["name"]
        ptype = group["_id"]["type"]

        # Get all protocols in this group, ordered by created_at (keep oldest)
        protos = await svc.get_all(
            filter={"name": name, "type": ptype},
            limit=100,
        )
        protos.sort(key=lambda p: p.created_at or "")

        keeper = protos[0]
        duplicates = protos[1:]

        for dup in duplicates:
            # Re-point any agent_protocol references to the keeper
            agent_protos = await ap_svc.get_all(filter={"protocol_id": dup.id}, limit=500)
            for ap in agent_protos:
                # Check if keeper is already assigned to this agent
                existing = await ap_svc.find_one({
                    "agent_id": ap.agent_id,
                    "protocol_id": keeper.id,
                })
                if existing:
                    await ap_svc.delete(ap.id)
                else:
                    await ap_svc.update(ap.id, {"protocol_id": keeper.id})

            await svc.delete(dup.id)
            removed += 1

    return removed
