"""
Video Search Agent - LangGraph ReactAgent implementation

This agent handles video search requests through video search tools:
- SearchVideos: Opens browser and searches for videos on videocenter or YouTube

The agent supports two video services:
- videocenter (default/preferred)
- youtube (when explicitly requested)

The agent is designed to be used by supervisor_agent and implements 
LangGraph's create_react_agent pattern.
"""

import asyncio
import logging

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from realtime_function_seach_videos import SearchVideos


def create_video_search_agent(model_name: str = "gpt-4o-mini", temperature: float = 0.1):
    """
    Create a video search agent for supervisor usage that supports videocenter and YouTube.
    
    Args:
        model_name: OpenAI model to use
        temperature: Model temperature for response generation
        
    Returns:
        LangGraph ReactAgent: Agent executor ready for supervisor
    """
    # System prompt for video search with service selection
    system_prompt = """
You are a specialized assistant for video search and content discovery across multiple platforms.

SUPPORTED VIDEO SERVICES:
- videocenter (for movies and TV shows)
- youtube (for general video content)

SERVICE SELECTION RULES:
1. VIDEOCENTER: Use "videocenter" for movie and TV show content:
   - When user mentions specific movie or TV show titles
   - When user wants to watch specific movie/TV content
   - When conversation context involves movie/TV titles
   - Any content that appears to be movie or TV show titles

2. YOUTUBE: Use "youtube" for all other video searches:
   - General video searches (cooking, tutorials, music, etc.)
   - Educational content, how-to videos
   - Entertainment videos (cats, funny videos, etc.)
   - Any non-movie/TV content

EXAMPLES OF SERVICE SELECTION:
✅ videocenter (movies/TV shows):
- "スターウォーズを検索して" → service="videocenter"
- "スターウォーズを見たい" → service="videocenter"
- "Search for Star Wars" → service="videocenter"
- "I want to watch The Matrix" → service="videocenter"
- "鬼滅の刃の動画を探して" → service="videocenter"
- "アベンジャーズを見せて" → service="videocenter"

✅ youtube (general videos):
- "猫の動画を探して" → service="youtube"
- "料理動画を検索して" → service="youtube"
- "Search for cooking tutorials" → service="youtube"
- "ギターのレッスン動画" → service="youtube"
- "面白い動画を見たい" → service="youtube"
- "How to play piano" → service="youtube"

USE THE TOOL:
- search_videos: Search for videos with appropriate service selection based on content type

Video search capabilities:
- Search for movies and TV shows on videocenter platform
- Search for general video content on youtube platform
- Support for various content types across both platforms

CRITICAL INSTRUCTION:
After executing the search_videos tool, if the tool output contains 'return_direct': true,
return the tool output as-is without any additional comments or explanations.
If the tool output is JSON, return the JSON as a string exactly as it is.

Always respond in the same language as the user's input. However, for return_direct cases, 
return the tool output exactly as provided by the tool.
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
        name="video_search_agent"  # Updated name for supervisor
    )
    
    logging.info("Created Video Search agent for supervisor (videocenter + YouTube support)")
    return agent_executor


# Simple JSON validation
def validate_basic_json_format(response_str: str) -> tuple[bool, str]:
    """
    Basic validation for video search agent response JSON format.
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
        
        # Check if service is videocenter or youtube
        search_videos_data = intent.get("webbrowser", {}).get("search_videos", {})
        service = search_videos_data.get("service", "")
        if service not in ["videocenter", "youtube"]:
            return False, f"Invalid service: {service}. Must be 'videocenter' or 'youtube'"
        
        return True, f"Basic JSON format OK (service: {service})"
        
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


# Example usage and testing with supervisor
async def main():
    """Test Video Search Agent through LangGraph supervisor with validation"""
    logging.basicConfig(level=logging.INFO)
    
    # Import required components for supervisor
    from langchain.chat_models import init_chat_model
    from langgraph_supervisor import create_supervisor
    
    print("=== Testing Video Search Agent via Supervisor ===")
    print("Services supported: videocenter (movies/TV), youtube (general videos)")
    
    # Create video search agent
    video_search_agent = create_video_search_agent()
    
    # Create a simple supervisor with only the video search agent
    supervisor = create_supervisor(
        model=init_chat_model("openai:gpt-4o-mini"),
        agents=[
            video_search_agent,
        ],
        prompt=(
            "You are a supervisor managing a video search agent.\n"
            "- VideoSearchAgent: Handles video search requests for videocenter and YouTube platforms.\n\n"
            
            "ASSIGNMENT RULES:\n"
            "1. For any video search or content discovery related requests, delegate to VideoSearchAgent.\n"
            "2. The VideoSearchAgent will automatically determine the appropriate service (videocenter or youtube).\n"
            "3. Always respond in the same language as the user's query (Japanese, English, etc.).\n"
            "4. Do not perform any work yourself - always delegate to the appropriate agent.\n\n"
            
            "IMPORTANT RULE FOR RETURN_DIRECT:\n"
            "If the worker's response contains JSON with 'return_direct': true, you MUST return that exact response without any modifications, additions, or explanations.\n"
            "Do not add any commentary or processing. Simply pass through the worker's response as-is to the user.\n"
            "Example: If worker returns JSON like {'type': 'tools.search_videos', 'return_direct': true, ...}, return exactly that JSON string.\n"
        ),
        add_handoff_back_messages=True,
        output_mode="full_history",
    ).compile()
    
    # Test messages - mix of movies/TV (videocenter) and general videos (youtube)
    test_messages = [
        # videocenter (movies/TV shows) cases
        "スターウォーズを検索して",  # Should use videocenter
        "スターウォーズを見たい",  # Should use videocenter
        "Search for Star Wars",  # Should use videocenter
        "I want to watch The Matrix",  # Should use videocenter
        "鬼滅の刃の動画を探して",  # Should use videocenter
        "アベンジャーズを見せて",  # Should use videocenter
        
        # youtube (general videos) cases
        "猫の動画を探して",  # Should use youtube
        "料理動画を検索して",  # Should use youtube  
        "Search for cooking tutorials",  # Should use youtube
        "ギターのレッスン動画を検索してください",  # Should use youtube
        "面白い動画を見たい",  # Should use youtube
        "How to play piano",  # Should use youtube
    ]
    
    # Track test results
    total_tests = len(test_messages)
    passed_tests = 0
    videocenter_tests = 0
    youtube_tests = 0
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. User: {message}")
        print("   Supervisor delegating to Video Search Agent...")
        
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
        
        # Validation with service detection
        if final_response:
            is_valid, error_msg = validate_basic_json_format(final_response)
            if is_valid:
                print(f"   ✅ TEST RESULT: {error_msg}")
                passed_tests += 1
                
                # Count service usage
                try:
                    import json
                    response_data = json.loads(final_response)
                    service = response_data.get("intent", {}).get("webbrowser", {}).get("search_videos", {}).get("service", "")
                    if service == "videocenter":
                        videocenter_tests += 1
                    elif service == "youtube":
                        youtube_tests += 1
                except:
                    pass
                    
            else:
                print(f"   ❌ TEST RESULT: JSON Format NG - {error_msg}")
        else:
            print("   ❌ TEST RESULT: No response received")
        
        print("   " + "="*50)
    
    # Print overall test summary
    print(f"\n{'='*60}")
    print(f"VIDEO SEARCH TEST SUMMARY: {passed_tests}/{total_tests} tests passed")
    print(f"Service Usage: videocenter={videocenter_tests}, youtube={youtube_tests}")
    
    if passed_tests == total_tests:
        print("🎉 ALL JSON FORMATS OK!")
        print("📝 EXPECTED SERVICE DISTRIBUTION:")
        print("   - videocenter: Movies and TV shows")
        print("   - youtube: General video content (tutorials, music, etc.)")
        print("📋 MANUAL VERIFICATION NEEDED:")
        print("   - Check that service selection matches content type")
        print("   - Verify search terms are appropriate")
        print("   - Confirm return_direct is set to true")
    else:
        print(f"⚠️  {total_tests - passed_tests} tests failed JSON format check")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
