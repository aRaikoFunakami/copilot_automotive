"""
Air Control Agent - LangGraph ReactAgent implementation

This agent handles air conditioning control requests through two main tools:
- AirControl: Sets absolute temperature values
- AirControlDelta: Adjusts temperature by relative values

The agent is designed to be used by supervisor_agent and implements 
LangGraph's create_react_agent pattern.
"""

import asyncio
import logging

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from function_aircontrol import AirControl, AirControlDelta


def create_aircontrol_agent(model_name: str = "gpt-4o-mini", temperature: float = 0.1):
    """
    Create an air control agent for supervisor usage.
    
    Args:
        model_name: OpenAI model to use
        temperature: Model temperature for response generation
        
    Returns:
        LangGraph ReactAgent: Agent executor ready for supervisor
    """
    # System prompt for air conditioning control
    system_prompt = """
あなたは車載エアコン制御の専門アシスタントです。

以下のツールを使用してエアコンを制御してください：
- intent_aircontrol: 絶対温度を設定する（例：22度に設定）
- intent_aircontrol_delta: 現在の設定温度からの相対変更（例：2度上げる、3度下げる）

制約：
- 設定可能温度範囲：18°C〜30°C
- 温度は0.5度刻みで設定してください
- ユーザーの要求を理解し、適切なツールを選択してください

ユーザーの要求例：
- "エアコンを22度に設定して" → intent_aircontrol を使用
- "もう少し涼しくして" → intent_aircontrol_delta を使用（-1〜-3度程度）
- "暖かくして" → intent_aircontrol_delta を使用（+1〜+3度程度）

常に日本語で丁寧に応答してください。
    """
    
    # Initialize components
    memory = MemorySaver()
    model = ChatOpenAI(model_name=model_name, temperature=temperature)
    tools = [AirControl(), AirControlDelta()]
    
    # Create and return react agent with name
    agent_executor = create_react_agent(
        model, 
        tools, 
        checkpointer=memory,
        prompt=system_prompt,
        name="aircontrol_agent"  # Add name for supervisor
    )
    
    logging.info("Created air control agent for supervisor")
    return agent_executor


# Example usage and testing with supervisor
async def main():
    """Test AirControl Agent through LangGraph supervisor"""
    logging.basicConfig(level=logging.INFO)
    
    # Import required components for supervisor
    from langchain.chat_models import init_chat_model
    from langgraph_supervisor import create_supervisor
    
    print("=== Testing AirControl Agent via Supervisor ===")
    
    # Create air control agent
    aircontrol_agent = create_aircontrol_agent()
    
    # Create a simple supervisor with only the aircontrol agent
    supervisor = create_supervisor(
        model=init_chat_model("openai:gpt-4o-mini"),
        agents=[
            aircontrol_agent,
        ],
        prompt=(
            "You are a supervisor managing an air conditioning control agent.\n"
            "- AirControlAgent: Handles air conditioning control requests including temperature settings and adjustments.\n\n"
            
            "ASSIGNMENT RULES:\n"
            "1. For any air conditioning or temperature related requests, delegate to AirControlAgent.\n"
            "2. Always respond in the same language as the user's query.\n"
            "3. Do not perform any work yourself - always delegate to the appropriate agent.\n"
        ),
        add_handoff_back_messages=True,
        output_mode="full_history",
    ).compile()
    
    # Test messages
    test_messages = [
        "エアコンを22度に設定してください",
        "もう少し涼しくしてください", 
        "3度暖かくして",
        "18度にして"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. User: {message}")
        print("   Supervisor delegating to AirControl Agent...")
        
        # Run through supervisor
        result_messages = []
        for chunk in supervisor.stream({
            "messages": [{"role": "user", "content": message}]
        }):
            for node_name, node_update in chunk.items():
                if "messages" in node_update and node_update["messages"]:
                    result_messages.extend(node_update["messages"])
        
        # Get the final response
        final_response = None
        for msg in reversed(result_messages):
            if isinstance(msg, dict):
                if msg.get("role") == "assistant":
                    final_response = msg.get("content")
                    break
            elif hasattr(msg, "content"):
                final_response = msg.content
                break
        
        print(f"   Supervisor Response: {final_response}")
        print("   " + "="*50)


if __name__ == "__main__":
    asyncio.run(main())