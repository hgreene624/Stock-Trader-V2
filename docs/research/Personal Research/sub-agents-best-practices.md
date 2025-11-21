# How to Properly Use Sub-Agents in Claude Code

Based on video: "I was using sub-agents wrong... Here is my way after 20+ hrs test"

## Core Purpose of Sub-Agents

Sub-agents were introduced primarily for **context optimization and token management**, not for direct implementation. They prevent the main agent from consuming too much of its context window by delegating research tasks that would otherwise fill up conversation history with large file contents.

## Key Best Practices

### 1. Use Sub-Agents as Researchers, Not Implementers
- Sub-agents work best when they're looking for information and providing small summaries back to the main conversation
- Avoid having sub-agents do actual implementation work
- Each sub-agent should focus on planning and research that improves the AI coding workflow

### 2. The Problem with Implementation Sub-Agents
- If a sub-agent implements something incorrectly, fixing it becomes difficult because:
  - Each sub-agent only knows about its specific task session
  - The parent agent doesn't see all the actions taken by sub-agents
  - Context isn't shared well across different agents
  - Each task is a very contained session with limited information flow

### 3. File System as Context Management
- Create a `.claude/docs/tasks/` folder structure to store context
- Have the parent agent create context files with project information
- Sub-agents should read the context file before starting work
- After finishing, sub-agents update the context file and save research reports as markdown files
- This allows all agents to access shared context by reading these files

### 4. Design Service-Specific Expert Sub-Agents
- Create specialized sub-agents for each service/technology (e.g., Shadcn expert, Vercel AI SDK expert, Stripe expert)
- Load them with latest documentation and best practices
- Equip them with relevant MCP tools for their specialty
- Have them analyze your codebase and create implementation plans

### 5. Sub-Agent Configuration Rules
- **Goal**: Design and propose detailed implementation plans, never do actual implementation
- **Before starting**: Read the context file to understand the overall project
- **After finishing**: Update the context file with what was done and save research reports
- **Output format**: Clearly indicate where the plan file is saved so the parent agent knows to read it
- Include rules preventing sub-agents from doing implementation

### 6. Workflow Structure
1. Parent agent creates context file for the feature/task
2. Parent agent delegates research to specialized sub-agent
3. Sub-agent reads context file
4. Sub-agent does research using specialized tools/knowledge
5. Sub-agent creates detailed implementation plan in markdown file
6. Sub-agent updates context file
7. Parent agent reads the plan
8. Parent agent does the actual implementation (not the sub-agent)

## Why This Works Better

- The parent agent maintains full context of what's been implemented
- When bugs occur, the parent agent can fix them effectively since it did the implementation
- Token consumption is dramatically reduced (massive read operations become small summaries)
- Each sub-agent becomes a domain expert with specialized knowledge and tools
- Context is preserved through the file system rather than conversation history

## Key Takeaway

The speaker emphasized that this approach "dramatically improved the success rate and result" after testing for 20+ hours. The fundamental principle is: **sub-agents are researchers and planners, while the parent agent is the implementer**.

SOURCE: https://www.youtube.com/watch?v=LCYBVpSB0Wo
