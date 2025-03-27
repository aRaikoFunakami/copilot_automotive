import asyncio
import uuid
import logging
import json
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from dummy_data.scenario_video import scenario_data
from agent_video_suggestion_ai import VideoRecommender

AGENT_MODES = ["video", "schedule"]

SYSTEM_PROMPT = {
    "video": '''
You are an in-vehicle entertainment assistant. 
Analyze the user's preferences and current vehicle conditions, and generate search parameters 
for the video recommendation engine.

Output JSON format:
{
    "video_search_params": { 
        "max_duration_sec": <int, maximum duration (in seconds) based on driving or charging status>,
        "viewer_role": <"driver" or "passenger", depending on who is watching>,
        "viewer_age": <int, age of the viewer>,
        "preferred_genres": <list of strings, genres the viewer prefers>,
        "avoid_recently_watched": <bool, true if user wants to avoid rewatching>,
        "driving_status": <string, e.g., "autonomous", "charging", or "manual">,
        "network_condition": <string, e.g., "good", "poor">,
        "session_id": <string, unique identifier for this session>,
        "reason": "A concise explanation describing why these parameters were set, referencing the user's preferences and vehicle conditions (e.g., battery level, ETA, passenger role)."
    }
}
'''
,
    "schedule": '''
You are a schedule management assistant. 
Analyze the vehicle status and calendar events to determine if the user might be late. 

Output JSON format:
{
  "proposal": {
    "title": "Late Notification Title",
    "reason": "Reason for delay",
    "action": "Specific notification content for the user"
  }
}
'''
}



class AgentDriverAssistAI:
    """LangChain-based agent manager"""

    def __init__(self, model_name: str = "gpt-4o") -> None:
        self.model_name = model_name
        self.agents: Dict[str, Dict[str, Any]] = {}

    def create_agent(self, thread_id: str = None) -> str:
        """Create a new agent with thread ID"""
        thread_id = thread_id or str(uuid.uuid4())
        if thread_id not in self.agents:
            models = {mode: ChatOpenAI(model_name=self.model_name) for mode in AGENT_MODES}
            self.agents[thread_id] = {"models": models}
        return thread_id

    async def run_agent(self, user_data: str, thread_id: str) -> Dict[str, Any]:
        """Run agent tasks for all modes and process video recommendation"""
        if thread_id not in self.agents:
            raise ValueError(f"Thread ID {thread_id} not found. Create an agent first.")

        agent_models = self.agents[thread_id]["models"]
        parser = JsonOutputParser()

        chains = {
            mode: PromptTemplate(
                template="{system_prompt}\n{format_instructions}\n{user_input}\n",
                input_variables=["user_input", "system_prompt"],
                partial_variables={"format_instructions": parser.get_format_instructions()},
            ) | agent_models[mode] | parser
            for mode in AGENT_MODES
        }

        #logging.info("user_data: " + user_data)
        # Run both video and schedule concurrently
        tasks = [
            chains[mode].ainvoke({
                "user_input": user_data,
                "system_prompt": SYSTEM_PROMPT[mode]
            }) for mode in AGENT_MODES
        ]
        results = await asyncio.gather(*tasks)

        # Store results separately
        video_response, schedule_response = results
        final_response = {
            "video_search_params": video_response,
            "schedule_proposal": schedule_response
        }

        # Extract video search params and run recommender
        if "video_search_params" in video_response:
            recommender = VideoRecommender()
            video_proposal = await recommender.recommend(video_response["video_search_params"])
            # ここで return_direct を video_proposal レイヤーに追加する
            if isinstance(video_proposal, dict):
                video_proposal["return_direct"] = True  # 必ずdict内に格納する
                video_proposal["type"] = "proposal_video"
            final_response["video_proposal"] = video_proposal

        final_response_str = json.dumps(final_response, ensure_ascii=False, indent=2)
        # logging.info(final_response_str)
        return final_response_str

    async def run_tasks(self, messages_per_thread: Dict[str, list]) -> None:
        """Batch process for multiple threads and messages"""
        tasks = [
            self.run_agent(message, thread_id)
            for thread_id, messages in messages_per_thread.items()
            for message in messages
        ]
        await asyncio.gather(*tasks)


async def main():
    """Main execution entry"""
    chat_manager = AgentDriverAssistAI()
    thread_id = chat_manager.create_agent("thread_123")

    for vehicle_status in scenario_data:
        vehicle_status_json = json.dumps(vehicle_status, ensure_ascii=False, indent=2)
        logging.info(f"Vehicle status: {vehicle_status_json}")
        responses = await chat_manager.run_agent(vehicle_status_json, thread_id)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    
    asyncio.run(main())