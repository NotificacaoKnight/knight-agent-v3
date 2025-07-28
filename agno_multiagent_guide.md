# Building Multiagent Systems with Agno Python Framework

## Overview

Agno is a Python framework for building multi-agent systems with shared memory, knowledge, and reasoning. It provides a powerful and flexible architecture for creating agents that can work individually or collaborate in teams to solve complex tasks.

## Installation

### 1. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Agno and Dependencies

```bash
# Core installation
pip install agno

# Additional dependencies for common use cases
pip install openai anthropic duckduckgo-search yfinance lancedb tantivy pypdf requests exa-py newspaper4k lxml_html_clean sqlalchemy
```

### 3. Set Up API Keys

Export your API keys for the models you plan to use:

```bash
# Choose one or more model providers
export OPENAI_API_KEY=your_openai_key
export ANTHROPIC_API_KEY=your_anthropic_key
export GROQ_API_KEY=your_groq_key
```

## Key Concepts

### 1. **Agents**: The atomic unit of work
- Agents are specialized entities with specific roles and tools
- Each agent has a model, instructions, and optional tools
- Agents work best with narrow scope and focused responsibilities

### 2. **Teams**: Multiple agents working together
- **Route Mode**: Team leader routes requests to appropriate members
- **Coordinate Mode**: Team leader delegates tasks and synthesizes outputs
- **Collaborate Mode**: All members work on the same task

### 3. **Workflows**: Deterministic, stateful multi-agent programs
- Written in pure Python for maximum control
- Supports state management, caching, and complex logic
- Best for production applications requiring reliability

## Example 1: Simple Two-Agent System

Create a file `simple_multiagent.py`:

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools

# Create specialized agents
researcher = Agent(
    name="Research Agent",
    role="Expert at finding and analyzing information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    instructions=["Always include sources", "Focus on factual information"],
)

writer = Agent(
    name="Writing Agent",
    role="Expert at creating clear, engaging content",
    model=OpenAIChat(id="gpt-4o"),
    instructions=["Write in a clear, concise style", "Structure content logically"],
)

# Create a team with coordinate mode
content_team = Team(
    name="Content Creation Team",
    mode="coordinate",  # Team leader coordinates between agents
    model=OpenAIChat(id="gpt-4o"),
    members=[researcher, writer],
    instructions=[
        "First, have the researcher gather information",
        "Then, have the writer create content based on the research",
        "Ensure the final output is comprehensive and well-structured",
    ],
    markdown=True,
    show_members_responses=True,
)

if __name__ == "__main__":
    # Run the team
    content_team.print_response(
        "Create a comprehensive guide about quantum computing basics",
        stream=True
    )
```

## Example 2: Advanced Financial Analysis Team

Create a file `financial_multiagent.py`:

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.yfinance import YFinanceTools

# Web research agent
web_agent = Agent(
    name="Web Research Agent",
    role="Handle web search requests and general research",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    instructions=["Always include sources", "Focus on recent information"],
    add_datetime_to_instructions=True,
)

# Financial data agent
finance_agent = Agent(
    name="Finance Agent",
    role="Handle financial data requests and market analysis",
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        YFinanceTools(
            stock_price=True,
            stock_fundamentals=True,
            analyst_recommendations=True,
            company_info=True
        )
    ],
    instructions=[
        "Use tables to display stock data",
        "Include P/E ratios, market cap, and key metrics",
        "Provide actionable insights",
    ],
    add_datetime_to_instructions=True,
)

# Create a reasoning-enabled team
financial_analysis_team = Team(
    name="Financial Analysis Team",
    mode="coordinate",
    model=Claude(id="claude-3-5-sonnet-20241022"),  # Using Claude for reasoning
    members=[web_agent, finance_agent],
    tools=[ReasoningTools(add_instructions=True)],  # Add reasoning capabilities
    instructions=[
        "Collaborate to provide comprehensive financial analysis",
        "Consider both fundamental analysis and market sentiment",
        "Use reasoning to analyze complex financial relationships",
        "Present findings in a structured, professional format",
        "Include risk assessment and recommendations",
    ],
    markdown=True,
    show_members_responses=True,
    enable_agentic_context=True,
)

if __name__ == "__main__":
    # Example: Compare tech giants
    financial_analysis_team.print_response(
        """Analyze and compare AAPL, GOOGL, and MSFT:
        1. Get current financial metrics
        2. Research recent news and market sentiment
        3. Provide investment recommendations with reasoning""",
        stream=True,
        show_full_reasoning=True,
    )
```

## Example 3: Workflow-Based Multiagent System

Create a file `workflow_multiagent.py`:

```python
from typing import Iterator
from agno.agent import Agent, RunResponse
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.workflow import Workflow
from agno.utils.log import logger

class ResearchWorkflow(Workflow):
    """A workflow that coordinates multiple agents for research tasks"""
    
    # Define agents as workflow attributes
    searcher = Agent(
        name="Search Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGoTools()],
        instructions=["Find relevant information", "Focus on authoritative sources"]
    )
    
    analyzer = Agent(
        name="Analysis Agent",
        model=OpenAIChat(id="gpt-4o"),
        instructions=["Analyze information critically", "Identify key insights"]
    )
    
    synthesizer = Agent(
        name="Synthesis Agent",
        model=OpenAIChat(id="gpt-4o"),
        instructions=["Create comprehensive summaries", "Structure information clearly"]
    )
    
    def run(self, topic: str, num_sources: int = 3) -> Iterator[RunResponse]:
        """
        Execute the research workflow
        
        Args:
            topic: The research topic
            num_sources: Number of sources to analyze
        """
        logger.info(f"Starting research workflow for: {topic}")
        
        # Step 1: Search for information
        search_query = f"Find {num_sources} authoritative sources about {topic}"
        logger.info("Step 1: Searching for sources...")
        
        search_response = None
        for response in self.searcher.run(search_query, stream=True):
            search_response = response
            yield response
        
        # Store search results in workflow state
        if search_response:
            self.session_state["search_results"] = search_response.content
            
        # Step 2: Analyze each source
        logger.info("Step 2: Analyzing sources...")
        analysis_query = f"""
        Analyze the following search results about {topic}:
        {self.session_state.get('search_results', 'No results found')}
        
        Provide critical analysis and identify key insights.
        """
        
        analysis_response = None
        for response in self.analyzer.run(analysis_query, stream=True):
            analysis_response = response
            yield response
            
        # Store analysis in workflow state
        if analysis_response:
            self.session_state["analysis"] = analysis_response.content
            
        # Step 3: Synthesize findings
        logger.info("Step 3: Synthesizing findings...")
        synthesis_query = f"""
        Based on the analysis below, create a comprehensive summary about {topic}:
        
        Analysis:
        {self.session_state.get('analysis', 'No analysis available')}
        
        Create a well-structured report with:
        1. Executive Summary
        2. Key Findings
        3. Detailed Analysis
        4. Conclusions and Recommendations
        """
        
        for response in self.synthesizer.run(synthesis_query, stream=True):
            yield response
            
        logger.info("Research workflow completed")

if __name__ == "__main__":
    # Create and run the workflow
    workflow = ResearchWorkflow()
    
    # Execute research on a topic
    topic = "Impact of AI on software development productivity"
    responses = workflow.run(topic=topic, num_sources=5)
    
    # Print the responses
    from agno.utils.pprint import pprint_run_response
    pprint_run_response(responses, markdown=True, show_time=True)
```

## Example 4: Multiagent System with Memory and Knowledge

Create a file `advanced_multiagent.py`:

```python
from pathlib import Path
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.knowledge.pdf import PDFReader, PDFKnowledge
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.embedder.openai import OpenAIEmbedder

# Setup paths
cwd = Path(__file__).parent
data_dir = cwd.joinpath("data")
data_dir.mkdir(exist_ok=True)

# Initialize memory system
memory_db = SqliteMemoryDb(
    table_name="team_memory",
    db_file=str(data_dir.joinpath("memory.db"))
)
memory = Memory(db=memory_db)

# Initialize knowledge base (if you have PDFs)
knowledge_base = PDFKnowledge(
    reader=PDFReader(),
    path=str(data_dir),  # Directory containing PDFs
    vector_db=LanceDb(
        uri=str(data_dir.joinpath("lancedb")),
        table_name="knowledge",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)

# Create specialized agents
research_agent = Agent(
    name="Research Specialist",
    role="Expert at finding and verifying information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    instructions=["Cross-reference multiple sources", "Verify facts"],
)

knowledge_agent = Agent(
    name="Knowledge Expert",
    role="Expert at using internal knowledge base",
    model=OpenAIChat(id="gpt-4o"),
    instructions=["Search internal documents first", "Cite sources"],
)

# Create team with memory and knowledge
intelligent_team = Team(
    name="Intelligent Research Team",
    mode="coordinate",
    model=OpenAIChat(id="gpt-4o"),
    members=[research_agent, knowledge_agent],
    memory=memory,
    knowledge=knowledge_base,
    enable_agentic_memory=True,
    enable_session_summaries=True,
    add_history_to_messages=True,
    num_history_runs=5,
    instructions=[
        "First check internal knowledge base",
        "Then search external sources if needed",
        "Remember important information from conversations",
        "Build on previous discussions",
    ],
    markdown=True,
)

if __name__ == "__main__":
    # Load knowledge base (run once)
    # knowledge_base.load()
    
    # First interaction
    intelligent_team.print_response(
        "My name is John and I'm interested in machine learning applications in healthcare",
        stream=True
    )
    
    # Second interaction - team remembers the user
    intelligent_team.print_response(
        "Based on my interests, what recent developments should I know about?",
        stream=True
    )
    
    # Get session summary
    summary = intelligent_team.get_session_summary()
    print(f"\nSession Summary: {summary.summary if summary else 'No summary available'}")
```

## Best Practices

### 1. Agent Design
- Keep agents focused with specific roles
- Limit tools per agent (3-5 maximum)
- Write clear, specific instructions
- Use appropriate models for each agent's task

### 2. Team Modes
- **Route**: Use when agents have distinct expertise areas
- **Coordinate**: Use when tasks require sequential processing
- **Collaborate**: Use when you need multiple perspectives

### 3. Workflow vs Team
- **Use Workflows when**:
  - You need deterministic execution
  - State management is critical
  - You want full control over the flow
  - Building production systems

- **Use Teams when**:
  - Tasks are more exploratory
  - You want agents to reason about coordination
  - Flexibility is more important than determinism

### 4. Performance Optimization
- Use appropriate models (GPT-4o for complex tasks, GPT-3.5 for simple ones)
- Enable streaming for better user experience
- Cache results when possible (in workflows)
- Use parallel processing where applicable

### 5. Error Handling
```python
try:
    response = team.run("Your query")
    print(response.content)
except Exception as e:
    logger.error(f"Team execution failed: {e}")
    # Implement fallback logic
```

## Monitoring and Debugging

### Enable Debug Mode
```python
team = Team(
    name="Debug Team",
    members=[agent1, agent2],
    debug_mode=True,  # Shows detailed execution logs
    show_tool_calls=True,  # Shows when tools are called
    show_members_responses=True,  # Shows individual agent responses
)
```

### Monitoring with Agno Dashboard
Agno provides monitoring at [app.agno.com](https://app.agno.com). Configure monitoring:

```python
team = Team(
    name="Monitored Team",
    members=[agent1, agent2],
    api_key="your_agno_api_key",  # Enable monitoring
)
```

## Running Your Multiagent System

1. Save one of the example files
2. Ensure you have the required API keys exported
3. Run the script:

```bash
python simple_multiagent.py
```

## Next Steps

1. Experiment with different team modes
2. Add custom tools for your specific use cases
3. Implement memory for persistent conversations
4. Build production workflows for complex tasks
5. Explore the [Agno documentation](https://docs.agno.com) for advanced features

Remember: Start simple with 2-3 agents, test thoroughly, then scale up as needed.