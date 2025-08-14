"""
Car Navigation Agent - LangGraph ReactAgent implementation

This agent handles car navigation requests through navigation tools:
- LaunchNavigation: Starts navigation to specified destinations using coordinates or place names

The agent is designed to be used by supervisor_agent and implements 
LangGraph's create_react_agent pattern.
"""

import asyncio
import logging

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from function_launch_navigation import LaunchNavigation


def create_carnavigation_agent(model_name: str = "gpt-4o-mini", temperature: float = 0.1):
    """
    Create a car navigation agent for supervisor usage.
    
    Args:
        model_name: OpenAI model to use
        temperature: Model temperature for response generation
        
    Returns:
        LangGraph ReactAgent: Agent executor ready for supervisor
    """
    # System prompt for car navigation control
    system_prompt = """
You are a specialized assistant for vehicle navigation control.

Use the following tools to control navigation:
- intent_googlenavigation: Launch navigation to a specified destination using coordinates or place names

Navigation capabilities:
- Navigate using destination name (e.g., "Tokyo Tower", "Shibuya Station")
- Navigate using latitude and longitude coordinates
- Supports Google Maps integration

User request examples:
- "Navigate to Tokyo Tower" → use intent_googlenavigation with destination
- "Take me to Shibuya" → use intent_googlenavigation with destination  
- "Navigate to coordinates 35.6762, 139.6503" → use intent_googlenavigation with lat/lng
- "Go to the nearest convenience store" → use intent_googlenavigation with destination

Important rule:
After executing a tool, if the tool output contains 'return_direct': true,
return the tool output as-is without any additional comments or explanations.
If the tool output is JSON, return the JSON as a string exactly as it is.

Always respond in the same language as the user's input. However, for return_direct cases, return the tool output exactly as provided.
    """
    
    # Initialize components
    memory = MemorySaver()
    model = ChatOpenAI(model_name=model_name, temperature=temperature)
    tools = [LaunchNavigation()]
    
    # Create and return react agent with name
    agent_executor = create_react_agent(
        model, 
        tools, 
        checkpointer=memory,
        prompt=system_prompt,
        name="carnavigation_agent"  # Add name for supervisor
    )
    
    logging.info("Created car navigation agent for supervisor")
    return agent_executor


# Simple JSON validation
def validate_basic_json_format(response_str: str) -> tuple[bool, str]:
    """
    Basic validation for CarNavigation agent response JSON format.
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
    """Test CarNavigation Agent through LangGraph supervisor with validation"""
    logging.basicConfig(level=logging.INFO)
    
    # Import required components for supervisor
    from langchain.chat_models import init_chat_model
    from langgraph_supervisor import create_supervisor
    
    print("=== Testing CarNavigation Agent via Supervisor ===")
    
    # Create car navigation agent
    carnavigation_agent = create_carnavigation_agent()
    
    # Create a simple supervisor with only the carnavigation agent
    supervisor = create_supervisor(
        model=init_chat_model("openai:gpt-4o-mini"),
        agents=[
            carnavigation_agent,
        ],
        prompt=(
            "You are a supervisor managing a car navigation control agent.\n"
            "- CarNavigationAgent: Handles navigation requests including destination routing and GPS navigation.\n\n"
            
            "ASSIGNMENT RULES:\n"
            "1. For any navigation, routing, or destination related requests, delegate to CarNavigationAgent.\n"
            "2. Always respond in the same language as the user's query (Japanese, English, etc.).\n"
            "3. Do not perform any work yourself - always delegate to the appropriate agent.\n\n"
            
            "IMPORTANT RULE FOR RETURN_DIRECT:\n"
            "If the worker's response contains JSON with 'return_direct': true, you MUST return that exact response without any modifications, additions, or explanations.\n"
            "Do not add any commentary or processing. Simply pass through the worker's response as-is to the user.\n"
            "Example: If worker returns JSON like {'type': 'tools.launch_navigation', 'return_direct': true, ...}, return exactly that JSON string.\n"
        ),
        add_handoff_back_messages=True,
        output_mode="full_history",
    ).compile()
    
    # Test messages (Japanese and English)
    test_messages = [
        "東京タワーまでナビゲーションを開始してください",
        "Navigate to Shibuya Station",
        "渋谷駅に案内して",
        "Take me to Tokyo Skytree",
        "座標35.6762, 139.6503まで案内してください"
    ]
    
    # Track test results
    total_tests = len(test_messages)
    passed_tests = 0
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. User: {message}")
        print("   Supervisor delegating to CarNavigation Agent...")
        
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
                print("   📝 MANUAL CHECK: Please verify the destination and navigation parameters are correct")
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
        print("   - Destination values are appropriate")
        print("   - Navigation parameters are correct")
        print("   - return_direct is set to true")
    else:
        print(f"⚠️  {total_tests - passed_tests} tests failed JSON format check")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
