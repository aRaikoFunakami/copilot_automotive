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
You are a specialized assistant for vehicle air conditioning control.

Use the following tools to control the air conditioning:
- intent_aircontrol: Set absolute temperature (e.g., set to 22 degrees)
- intent_aircontrol_delta: Adjust temperature relative to current setting (e.g., raise by 2 degrees, lower by 3 degrees)

Constraints:
- Settable temperature range: 18°C to 30°C
- Set temperature in 0.5-degree increments
- Understand user requests and select the appropriate tool

User request examples:
- "Set air conditioning to 22 degrees" → use intent_aircontrol
- "Make it a little cooler" → use intent_aircontrol_delta (about -1 to -3 degrees)
- "Make it warmer" → use intent_aircontrol_delta (about +1 to +3 degrees)

Important rule:
After executing a tool, if the tool output contains 'return_direct': true,
return the tool output as-is without any additional comments or explanations.
If the tool output is JSON, return the JSON as a string exactly as it is.

Always respond in the same language as the user's input. However, for return_direct cases, return the tool output exactly as provided.
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


# Simple JSON validation
def validate_basic_json_format(response_str: str) -> tuple[bool, str]:
    """
    Basic validation for AirControl agent response JSON format.
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
    """Test AirControl Agent through LangGraph supervisor with validation"""
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
            "2. Always respond in the same language as the user's query (Japanese, English, etc.).\n"
            "3. Do not perform any work yourself - always delegate to the appropriate agent.\n\n"
            
            "IMPORTANT RULE FOR RETURN_DIRECT:\n"
            "If the worker's response contains JSON with 'return_direct': true, you MUST return that exact response without any modifications, additions, or explanations.\n"
            "Do not add any commentary or processing. Simply pass through the worker's response as-is to the user.\n"
            "Example: If worker returns JSON like {'type': 'tools.aircontrol', 'return_direct': true, ...}, return exactly that JSON string.\n"
        ),
        add_handoff_back_messages=True,
        output_mode="full_history",
    ).compile()
    
    # Test messages (Japanese and English)
    test_messages = [
        "エアコンを22度に設定してください",
        "Set the air conditioning to 20 degrees",
        "もう少し涼しくしてください", 
        "Make it 2 degrees warmer",
        "18度にして"
    ]
    
    # Track test results
    total_tests = len(test_messages)
    passed_tests = 0
    
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
        
        # Simple validation - only check basic JSON format
        if final_response:
            is_valid, error_msg = validate_basic_json_format(final_response)
            if is_valid:
                print("   ✅ TEST RESULT: JSON Format OK")
                print("   📝 MANUAL CHECK: Please verify the temperature values and tool selection are correct")
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
        print("   - Temperature values are appropriate")
        print("   - Tool selection matches user intent")
        print("   - return_direct is set to true")
    else:
        print(f"⚠️  {total_tests - passed_tests} tests failed JSON format check")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())