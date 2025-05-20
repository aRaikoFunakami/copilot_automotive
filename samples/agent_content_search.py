import asyncio
import uuid
from typing import Dict, Optional
import logging

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage, SystemMessage
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

        # Role instructions for the agent
        self.system_prompt = """
        あなたは動画コンテンツに関する情報をもとに、実在する映画、TVドラマ、またはアニメ作品のタイトルを提案するアシスタントです。

        絶対に架空のタイトルを作成してはいけません。現実に存在する作品名だけを提案してください。

        Tavily を使用することで、インターネット上の最新かつ信頼性のある情報を取得できます。
        Tavily を使って検索結果を取得した場合は、検索結果の中から最も該当しそうな作品を1つ選び、
        その作品のタイトルを明示的にユーザーに提示してください。
        その際、「この作品かもしれませんが、確証がないため、より詳しい情報を教えてください」といった表現で、
        確定ではないことを明示してください。

        該当する作品タイトルが見つからない場合や、情報が不足していると判断される場合は、すぐにタイトルを出さずに、ユーザーにさらに詳しい情報（例：年代、国、言語、ターゲット層、プロットの詳細など）を丁寧に質問してください。

        質問をする際には、現時点で最も該当しそうな候補を1作品だけ挙げてください。
        その際、「この作品かもしれませんが、確証がないため、より詳しい情報を教えてください」といった表現で、確定ではないことを明示してください。

        会話は自然な日本語で行い、ユーザーに対して丁寧かつ親切に応対してください。
        """


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

            agent_executor = create_react_agent(model, tools, checkpointer=memory, prompt=self.system_prompt)

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
            {"messages": [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=message),
                ]},
            config,
            stream_mode="values",
        ):
            response = step["messages"][-1].content  # Store latest response

        #logging.info(f"[Thread {thread_id}] {response}")  # Log the response
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

    # Create one agent thread
    thread1 = chat_manager.create_agent("thread_123")

    while True:
        user_input = input("Enter a message (or 'exit' to quit): ")
        if user_input.lower() == "exit":
            break
        response = await chat_manager.run_agent(user_input, thread1)
        logging.info(f"🎥 Generated Title: {response}")


# Run everything inside a single event loop
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())