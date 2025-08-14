
from langgraph_supervisor import create_supervisor
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI

# Import TMDB agent (installed via uv add --editable ./tmdb_agent)
from tmdb_agent.agent import create_tmdb_agent

# Import local agents
from aircontrol_agent import create_aircontrol_agent
from youtube_agent import create_youtube_agent
from carnavigation_agent import create_carnavigation_agent

# Import supervisor adaptor functions - REQUIRED!
# extract_user_input_multiple_patterns is used inside adapt_agent_executor_for_supervisor
# This function handles multiple message formats from LangChain/LangGraph
from supervisor_adaptor import adapt_agent_executor_for_supervisor, extract_user_input_multiple_patterns

# TMDBエージェントの初期化
tmdb_agent = create_tmdb_agent(
    llm=ChatOpenAI(model="gpt-4o-mini", temperature=0.1),
    verbose=True,
)

# 必須のadapt_agent_executor_for_supervisorを使用
tmdb_adapter = adapt_agent_executor_for_supervisor(
    agent_executor=tmdb_agent.agent_executor,
    name="tmdb_search_agent",
    debug=False
)


# 自動車関連エージェントの初期化
aircontrol_agent = create_aircontrol_agent(model_name="gpt-4o-mini", temperature=0.1)
youtube_agent = create_youtube_agent(model_name="gpt-4o-mini", temperature=0.1)
carnavigation_agent = create_carnavigation_agent(model_name="gpt-4o-mini", temperature=0.1)

# エージェントリストを構築（TMDBエージェントを含む）
agents_list = [
    aircontrol_agent,
    youtube_agent, 
    carnavigation_agent,
    tmdb_adapter,  # TMDBエージェントは常に存在すると仮定
]


supervisor = create_supervisor(
    model=init_chat_model("openai:gpt-4o-mini"),
    agents=agents_list,
    prompt=(
        "You are a supervisor managing automotive and entertainment agents:\n"
        "- AirControlAgent: Handles air conditioning control requests including temperature settings and adjustments.\n"
        "- YouTubeAgent: Handles YouTube video search requests and content discovery.\n"
        "- CarNavigationAgent: Handles navigation requests including destination routing and GPS navigation.\n"
        "- TMDBSearchAgent: Handles movie, TV show, and celebrity information searches using TMDB API.\n"
        "\n"
        
        "ASSIGNMENT RULES:\n"
        "1. For any air conditioning or temperature related requests, delegate to AirControlAgent.\n"
        "2. For any YouTube, video search, or content discovery related requests, delegate to YouTubeAgent.\n"
        "3. For any navigation, routing, or destination related requests, delegate to CarNavigationAgent.\n"
        "4. For movie, TV show, actor, director, or entertainment industry queries, delegate to TMDBSearchAgent.\n"
        "5. Always respond in the same language as the user's query (Japanese, English, etc.).\n"
        "6. Do not perform any work yourself - always delegate to the appropriate agent.\n\n"
        
        "TASK ROUTING EXAMPLES:\n"
        "- 'Set air conditioning to 22 degrees' → AirControlAgent\n"
        "- 'Search for cooking videos on YouTube' → YouTubeAgent\n"
        "- 'Navigate to Tokyo Station' → CarNavigationAgent\n"
        "- 'Tell me about the movie Inception' → TMDBSearchAgent\n"
        "- 'What movies has Tom Hanks appeared in?' → TMDBSearchAgent\n\n"
        
        "IMPORTANT RULE FOR RETURN_DIRECT:\n"
        "If the worker's response contains JSON with 'return_direct': true, you MUST return that exact response without any modifications, additions, or explanations.\n"
        "Do not add any commentary or processing. Simply pass through the worker's response as-is to the user.\n"
        "Example: If worker returns JSON like {'type': 'tools.aircontrol', 'return_direct': true, ...}, return exactly that JSON string.\n"
    ),
    add_handoff_back_messages=True,
    output_mode="full_history",
).compile()


# テスト用メイン関数
async def main():
    """Test Supervisor Agent with all automotive agents and TMDB search"""
    import logging
    
    logging.basicConfig(level=logging.INFO)
    print("=== Testing Supervisor Agent with All Agents (Including TMDB) ===")
    print("TMDB Agent Available: True (installed via uv add --editable)")
    print(f"Using extract_user_input_multiple_patterns: {extract_user_input_multiple_patterns is not None}")
    
    # テストメッセージ（TMDB検索を含む）
    test_messages = [
        "エアコンを22度に設定してください",
        "YouTubeで料理のレシピ動画を検索して",
        "東京駅までナビゲーションを開始してください",
        "映画「君の名は」について教えて",
        "トム・ハンクスが出演している映画を教えて",
        "Set the air conditioning to 20 degrees",
        "Search for funny cat videos on YouTube",
        "Tell me about the movie Inception"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. User: {message}")
        print("   Supervisor processing...")
        
        # Supervisorに送信
        result_messages = []
        for chunk in supervisor.stream({
            "messages": [{"role": "user", "content": message}]
        }):
            for node_name, node_update in chunk.items():
                if "messages" in node_update and node_update["messages"]:
                    result_messages.extend(node_update["messages"])
        
        # 最終レスポンスを取得
        final_response = None
        for msg in reversed(result_messages):
            if isinstance(msg, dict):
                if msg.get("role") == "assistant":
                    final_response = msg.get("content")
                    break
            elif hasattr(msg, "content"):
                final_response = msg.content
                break
        
        # レスポンスタイプを判定
        response_type = "Unknown"
        if final_response:
            if "tools.aircontrol" in str(final_response):
                response_type = "AirControl JSON"
            elif "tools.search_videos" in str(final_response):
                response_type = "YouTube Search JSON"
            elif "tools.launch_navigation" in str(final_response):
                response_type = "Navigation JSON"
            elif any(keyword in str(final_response).lower() for keyword in ["movie", "film", "actor", "director", "tmdb"]):
                response_type = "TMDB Search Result"
            else:
                response_type = "General Response"
        
        print(f"   Response Type: {response_type}")
        print(f"   Supervisor Response: {final_response}")
        print("   " + "="*50)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())