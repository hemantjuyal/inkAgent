import os
import warnings

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew, llm, tool
from crewai_tools import SerperDevTool
from tools.website_search_tool import WebsiteSearchTool
from langsmith import traceable

# Optional: Silence deprecated warnings (Pydantic 2.x)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Load environment variables first!
load_dotenv()

# Print API key status for debugging
print(f"GROQ_API_KEY set: {'Yes' if os.getenv('GROQ_API_KEY') else 'No'}")
print(f"SERPER_API_KEY set: {'Yes' if os.getenv('SERPER_API_KEY') else 'No'}")
print(f"LANGSMITH_API_KEY set: {'Yes' if os.getenv('LANGSMITH_API_KEY') else 'No'}")
print(f"LANGSMITH_TRACING set: {os.getenv('LANGSMITH_TRACING')}")
print(f"LANGSMITH_PROJECT set: {os.getenv('LANGSMITH_PROJECT')}")

@CrewBase
class InkAgentCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @llm
    def groq_llm(self):
        return ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model="groq/llama3-8b-8192",
            temperature=0.7,
            max_retries=5,
            timeout=60  # Add a timeout to prevent indefinite waits
        )

    @tool
    def serper_dev_tool(self):
        return SerperDevTool(api_key=os.getenv("SERPER_API_KEY"))

    @tool
    def website_search_tool(self):
        return WebsiteSearchTool()

    # Define all agents
    @agent
    def ink_agent(self) -> Agent:
        return Agent(
            role=self.agents_config['ink_agent']['role'],
            goal=self.agents_config['ink_agent']['goal'],
            backstory=self.agents_config['ink_agent']['backstory'],
            allow_delegation=self.agents_config['ink_agent']['allow_delegation'],
            llm=self.groq_llm(),
            verbose=self.agents_config['ink_agent']['verbose']
        )

    @agent
    def topic_strategy_agent(self) -> Agent:
        return Agent(
            role=self.agents_config['topic_strategy_agent']['role'],
            goal=self.agents_config['topic_strategy_agent']['goal'],
            backstory=self.agents_config['topic_strategy_agent']['backstory'],
            llm=self.groq_llm(),
            tools=[self.serper_dev_tool()],
            verbose=self.agents_config['topic_strategy_agent']['verbose']
        )

    @agent
    def content_research_agent(self) -> Agent:
        return Agent(
            role=self.agents_config['content_research_agent']['role'],
            goal=self.agents_config['content_research_agent']['goal'],
            backstory=self.agents_config['content_research_agent']['backstory'],
            llm=self.groq_llm(),
            tools=[self.website_search_tool()],
            verbose=self.agents_config['content_research_agent']['verbose']
        )

    @agent
    def writer_agent(self) -> Agent:
        return Agent(
            role=self.agents_config['writer_agent']['role'],
            goal=self.agents_config['writer_agent']['goal'],
            backstory=self.agents_config['writer_agent']['backstory'],
            llm=self.groq_llm(),
            verbose=self.agents_config['writer_agent']['verbose']
        )

    # Task
    @task
    def master_task(self) -> Task:
        return Task(
            description=self.tasks_config['master_task']['description'],
            expected_output=self.tasks_config['master_task']['expected_output'],
            agent=self.ink_agent()
        )

    # Crew definition
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.ink_agent(),
                self.topic_strategy_agent(),
                self.content_research_agent(),
                self.writer_agent()
            ],
            tasks=[self.master_task()],
            process=Process.sequential,
            verbose=True
        )


# Run the app
if __name__ == "__main__":
    crew = InkAgentCrew().crew()
    topic = input("📝 Enter a topic for the thought-leadership article: ")

    @traceable(name="Thought-Leadership Article Creation")
    def run_crew(topic):
        return crew.kickoff(inputs={"topic": topic})

    result = run_crew(topic)
    fname = f"{topic.lower().replace(' ', '_')}.md"
    with open(fname, "w") as f:
        f.write(result.raw if hasattr(result, "raw") else result)
    print(f"✅ Saved article to: {fname}")