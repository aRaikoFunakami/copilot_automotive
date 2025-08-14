"""
YouTube Agent - LangGraph ReactAgent implementation

This agent handles YouTube video search requests through video search tools:
- SearchVideos: Opens browser and searches for videos on YouTube

The agent is designed to be used by supervisor_agent and implements 
LangGraph's create_react_agent pattern.
"""

import asyncio
import logging

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from realtime_function_seach_videos import SearchVideos


def create_youtube_agent(model_name: str = "gpt-4o-mini", temperature: float = 0.1):
    """
    Create a YouTube search agent for supervisor usage.
    
    Args:
        model_name: OpenAI model to use
        temperature: Model temperature for response generation
        
    Returns:
        LangGraph ReactAgent: Agent executor ready for supervisor
    """
    # System prompt for YouTube video search control
    system_prompt = """
You are a specialized assistant for YouTube video search and content discovery.

Use the following tools to search for videos:
- search_videos: Search for videos on YouTube by opening browser and performing the search

YouTube search capabilities:
- Search for videos by keywords, topics, or phrases
- Open YouTube in browser with search results
- Support for various content types (music, tutorials, entertainment, etc.)

User request examples:
- "Search for funny cat videos on YouTube" → use search_videos with service="youtube"
- "Find cooking tutorials" → use search_videos with service="youtube" 
- "Look for music videos by Taylor Swift" → use search_videos with service="youtube"
- "Search for travel vlogs about Japan" → use search_videos with service="youtube"

Important rule:
After executing a tool, if the tool output contains 'return_direct': true,
return the tool output as-is without any additional comments or explanations.
If the tool output is JSON, return the JSON as a string exactly as it is.

Always respond in the same language as the user's input. However, for return_direct cases, return the tool output exactly as provided.
    """
    
    # Initialize components
    memory = MemorySaver()
    model = ChatOpenAI(model_name=model_name, temperature=temperature)
    tools = [SearchVideos()]
    
    # Create and return react agent with name
    agent_executor = create_react_agent(
        model, 
        tools, 
        checkpointer=memory,
        prompt=system_prompt,
        name="youtube_agent"  # Add name for supervisor
    )
    
    logging.info("Created YouTube search agent for supervisor")
    return agent_executor


# Simple JSON validation
def validate_basic_json_format(response_str: str) -> tuple[bool, str]:
    """
    Basic validation for YouTube agent response JSON format.
    Checks only essential fields existence - content validation should be done manually.
    
    Args:
        response_str: The response string to validate
        
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    import json
    
    try:
        # Parse JSON
        response_data = json.loads(response_str)
        
        # Check basic required fields only
        required_fields = ["type", "return_direct", "intent"]
        missing_fields = [field for field in required_fields if field not in response_data]
        
        if missing_fields:
            return False, f"Missing fields: {', '.join(missing_fields)}"
        
        # Basic check if intent has any content
        intent = response_data.get("intent", {})
        if not intent:
            return False, "Empty intent field"
        
        return True, "Basic JSON format OK"
        
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


# Example usage and testing with supervisor
async def main():
    """Test YouTube Agent through LangGraph supervisor with validation"""
    logging.basicConfig(level=logging.INFO)
    
    # Import required components for supervisor
    from langchain.chat_models import init_chat_model
    from langgraph_supervisor import create_supervisor
    
    print("=== Testing YouTube Agent via Supervisor ===")
    
    # Create YouTube agent
    youtube_agent = create_youtube_agent()
    
    # Create a simple supervisor with only the YouTube agent
    supervisor = create_supervisor(
        model=init_chat_model("openai:gpt-4o-mini"),
        agents=[
            youtube_agent,
        ],
        prompt=(
            "You are a supervisor managing a YouTube video search agent.\n"
            "- YouTubeAgent: Handles YouTube video search requests and content discovery.\n\n"
            
            "ASSIGNMENT RULES:\n"
            "1. For any YouTube, video search, or content discovery related requests, delegate to YouTubeAgent.\n"
            "2. Always respond in the same language as the user's query (Japanese, English, etc.).\n"
            "3. Do not perform any work yourself - always delegate to the appropriate agent.\n\n"
            
            "IMPORTANT RULE FOR RETURN_DIRECT:\n"
            "If the worker's response contains JSON with 'return_direct': true, you MUST return that exact response without any modifications, additions, or explanations.\n"
            "Do not add any commentary or processing. Simply pass through the worker's response as-is to the user.\n"
            "Example: If worker returns JSON like {'type': 'tools.search_videos', 'return_direct': true, ...}, return exactly that JSON string.\n"
        ),
        add_handoff_back_messages=True,
        output_mode="full_history",
    ).compile()
    
    # Test messages (Japanese and English)
    test_messages = [
        "YouTubeで面白い猫の動画を検索して",
        "Search for cooking tutorials on YouTube",
        "テイラー・スウィフトの音楽ビデオを探して",
        "Find travel vlogs about Japan",
        "YouTubeでギターのレッスン動画を検索してください"
    ]
    
    # Track test results
    total_tests = len(test_messages)
    passed_tests = 0
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. User: {message}")
        print("   Supervisor delegating to YouTube Agent...")
        
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
        
        # Simple validation - only check basic JSON format
        if final_response:
            is_valid, error_msg = validate_basic_json_format(final_response)
            if is_valid:
                print("   ✅ TEST RESULT: JSON Format OK")
                print("   📝 MANUAL CHECK: Please verify the search terms and YouTube parameters are correct")
                passed_tests += 1
            else:
                print(f"   ❌ TEST RESULT: JSON Format NG - {error_msg}")
        else:
            print("   ❌ TEST RESULT: No response received")
        
        print("   " + "="*50)
    
    # Print overall test summary
    print(f"\n{'='*60}")
    print(f"JSON FORMAT TEST SUMMARY: {passed_tests}/{total_tests} tests passed")
    if passed_tests == total_tests:
        print("🎉 ALL JSON FORMATS OK!")
        print("📝 IMPORTANT: Please manually verify:")
        print("   - Search terms are appropriate")
        print("   - YouTube service parameter is correct")
        print("   - return_direct is set to true")
    else:
        print(f"⚠️  {total_tests - passed_tests} tests failed JSON format check")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
