import asyncio
import uuid
from typing import Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent


class ChatAgent:
    """Reusable LangChain-based agent with persistent memory and thread management."""

    def __init__(self, model_name="gpt-4o", max_search_results=2):
        """
        Initialize the agent with model, search tool, and memory storage per thread.
        """
        self.model_name = model_name
        self.max_search_results = max_search_results
        self.agents: Dict[str, Dict] = {}  # Stores agents by thread_id

    def create_agent(self, thread_id: Optional[str] = None) -> str:
        """
        Create or retrieve an agent instance based on thread_id.
        If thread_id is not provided, a new one is generated.
        """
        if thread_id is None:
            thread_id = str(uuid.uuid4())  # Generate a unique thread ID

        if thread_id not in self.agents:
            memory = MemorySaver()
            model = ChatOpenAI(model_name=self.model_name)
            search = TavilySearchResults(max_results=self.max_search_results)
            tools = [search]
            agent_executor = create_react_agent(model, tools, checkpointer=memory)

            self.agents[thread_id] = {
                "executor": agent_executor,
                "memory": memory,
                "config": {"configurable": {"thread_id": thread_id}},
            }

        return thread_id  # Return thread_id so it can be reused externally

    async def run_agent(self, message: str, thread_id: str) -> str:
        """
        Run the agent asynchronously with a given message in a specified thread.
        Returns the last response from the LLM.
        """
        if thread_id not in self.agents:
            raise ValueError(f"Thread ID {thread_id} not found. Create an agent first.")

        agent_data = self.agents[thread_id]
        agent_executor = agent_data["executor"]
        config = agent_data["config"]

        response = None  # Store the last response

        async for step in agent_executor.astream(
            {"messages": [HumanMessage(content=message)]},
            config,
            stream_mode="values",
        ):
            response = step["messages"][-1].content  # Store latest response

        print(f"[Thread {thread_id}] {response}")  # Log the response
        return response  # Return the last response

    async def run_tasks(self, messages_per_thread: Dict[str, list]):
        """
        Run multiple agents concurrently in different threads.
        """
        tasks = []
        for thread_id, messages in messages_per_thread.items():
            for message in messages:
                tasks.append(self.run_agent(message, thread_id))
        results = await asyncio.gather(*tasks)  # Run all tasks concurrently
        return results  # Return all results


# --- Example Usage ---
async def main():
    chat_manager = ChatAgent()

    # Create two separate agent threads
    thread1 = chat_manager.create_agent("thread_123")
    thread2 = chat_manager.create_agent("thread_456")

    # Run first message for each thread and print results
    response1 = await chat_manager.run_agent("Hello, who are you?", thread1)
    print(f"Response1: {response1}")

    response2 = await chat_manager.run_agent("What is AI?", thread2)
    print(f"Response2: {response2}")

    # Multiple messages per thread
    messages_per_thread = {
        thread1: ["What is the capital of Japan?", "Tell me about LangChain."],
        thread2: ["Explain quantum computing.", "Who discovered relativity?"],
    }
    
    responses = await chat_manager.run_tasks(messages_per_thread)
    print(f"Responses: {responses}")

# Run everything inside a single event loop
if __name__ == "__main__":
    asyncio.run(main())