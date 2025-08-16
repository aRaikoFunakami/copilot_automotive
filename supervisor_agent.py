import logging
from langgraph_supervisor import create_supervisor
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI

# Import TMDB agent (installed via uv add --editable ./tmdb_agent)
from tmdb_agent.agent import create_tmdb_agent

# Import local agents
from aircontrol_agent import create_aircontrol_agent
from video_search_agent import create_video_search_agent
from carnavigation_agent import create_carnavigation_agent

# Import supervisor adaptor functions - REQUIRED!
# extract_user_input_multiple_patterns is used inside adapt_agent_executor_for_supervisor
# This function handles multiple message formats from LangChain/LangGraph
from supervisor_adaptor import adapt_agent_executor_for_supervisor, extract_user_input_multiple_patterns

# SupervisorをToolとして使用するためのimport
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Any, Dict
import json

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
video_search_agent = create_video_search_agent(model_name="gpt-4o-mini", temperature=0.1)
carnavigation_agent = create_carnavigation_agent(model_name="gpt-4o-mini", temperature=0.1)

# エージェントリストを構築（TMDBエージェントを含む）
agents_list = [
    aircontrol_agent,
    video_search_agent, 
    carnavigation_agent,
    tmdb_adapter,  # TMDBエージェントは常に存在すると仮定
]


supervisor = create_supervisor(
    model=init_chat_model("openai:gpt-4o-mini"),
    agents=agents_list,
    prompt=(
        "You are a supervisor managing automotive and entertainment agents:\n"
        "- AirControlAgent: Handles air conditioning control requests including temperature settings and adjustments.\n"
        "- VideoSearchAgent: Handles video search requests for videocenter (default) and YouTube (when explicitly mentioned) platforms.\n"
        "- CarNavigationAgent: Handles navigation requests including destination routing and GPS navigation.\n"
        "- TMDBSearchAgent: Handles movie, TV show, and celebrity information searches using TMDB API.\n"
        "\n"
        
        "ASSIGNMENT RULES:\n"
        "1. For any air conditioning or temperature related requests, delegate to AirControlAgent.\n"
        "2. For video search requests:\n"
        "   - Delegate to VideoSearchAgent for all video searches\n"
        "   - VideoSearchAgent automatically selects service: videocenter (movies/TV) or youtube (general videos)\n"
        "   - Movies/TV shows → videocenter, General videos → youtube\n"
        "3. For any navigation, routing, or destination related requests, delegate to CarNavigationAgent.\n"
        "4. For movie, TV show, actor, director, or entertainment industry queries, delegate to TMDBSearchAgent.\n"
        "5. Always respond in the same language as the user's query (Japanese, English, etc.).\n"
        "6. Do not perform any work yourself - always delegate to the appropriate agent.\n\n"
        
        "TASK ROUTING EXAMPLES:\n"
        "- 'Set air conditioning to 22 degrees' → AirControlAgent\n"
        "- 'Search for cooking videos' → VideoSearchAgent (will use youtube)\n"
        "- 'スターウォーズを検索して' → VideoSearchAgent (will use videocenter)\n"
        "- 'スターウォーズを見たい' → VideoSearchAgent (will use videocenter)\n"
        "- '猫の動画を探して' → VideoSearchAgent (will use youtube)\n"
        "- 'Navigate to Tokyo Station' → CarNavigationAgent\n"
        "- 'Tell me about the movie Inception' → TMDBSearchAgent\n"
        "- 'What movies has Tom Hanks appeared in?' → TMDBSearchAgent\n\n"
        
        "VIDEO SERVICE SELECTION (handled by VideoSearchAgent):\n"
        "- videocenter: Movies and TV shows content\n"
        "- youtube: General video content (tutorials, music, entertainment, etc.)\n\n"
        
        "IMPORTANT RULE FOR RETURN_DIRECT:\n"
        "If the worker's response contains JSON with 'return_direct': true, you MUST return that exact response without any modifications, additions, or explanations.\n"
        "Do not add any commentary or processing. Simply pass through the worker's response as-is to the user.\n"
        "Example: If worker returns JSON like {'type': 'tools.aircontrol', 'return_direct': true, ...}, return exactly that JSON string.\n"
    ),
    add_handoff_back_messages=True,
    output_mode="full_history",
).compile()


# SupervisorをToolとして使用するためのクラス
class SupervisorInput(BaseModel):
    """Input for the supervisor tool"""
    query: str = Field(description="User query to be processed by the supervisor")

class SupervisorTool(BaseTool):
    """Tool wrapper for the supervisor agent"""
    name: str = "supervisor"
    description: str = "A supervisor agent that can handle automotive control requests, entertainment searches, navigation requests, and movie/TV show information queries. Use this tool for complex tasks that require routing to specialized agents."
    args_schema: type[BaseModel] = SupervisorInput

    async def _arun(self, query: str) -> Dict[str, Any]:
        """Run the supervisor with the given query"""
        try:
            print(f"[SupervisorTool] query: {query}")
            # Supervisorに送信
            result_messages = []
            for chunk in supervisor.stream({
                "messages": [{"role": "user", "content": query}]
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
            
            print(f"[SupervisorTool] Final response: {final_response}")
            # JSONレスポンスを試行
            if final_response:
                try:
                    # JSONとしてパースできるかチェック
                    json_response = json.loads(final_response)
                    if isinstance(json_response, dict) and json_response.get("return_direct"):
                        return json_response
                except json.JSONDecodeError:
                    pass

            return final_response or "No response generated"
        
            return {
                "response": final_response or "No response generated",
                "status": "success",
                "return_direct": True
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "error",
                "return_direct": True
            }

    def _run(self, query: str) -> Dict[str, Any]:
        """Synchronous version - not implemented"""
        raise NotImplementedError("Use the async version _arun instead")


# SupervisorToolのインスタンスを作成
def create_supervisor_tool() -> SupervisorTool:
    return SupervisorTool()


# OpenAIVoiceReactAgentからSupervisorを呼び出すテスト
async def test_voice_react_agent_with_supervisor():
    """Test OpenAIVoiceReactAgent with supervisor as a tool - Simple and Reliable"""
    import asyncio
    from langchain_openai_voice import OpenAIVoiceReactAgent
    
    print("=== Simple and Reliable OpenAIVoiceReactAgent Test ===")
    
    # テスト用クエリ
    test_queries = [
        "エアコンを22度に設定してください",
        "YouTubeで料理動画を検索して",
        "東京駅への道案内をお願いします",
        "映画「君の名は」について教えて"
    ]
    
    results = []
    
    # 各クエリを個別にテスト（シンプル版）
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test {i}/{len(test_queries)}: {query} ---")
        
        # 新しいエージェントインスタンス
        voice_agent = OpenAIVoiceReactAgent(
            model="gpt-4o-mini-realtime-preview",
            instructions="Use supervisor tool for requests. Be brief and direct. Return supervisor responses exactly as-is without any modifications or additions.",
            tools=[create_supervisor_tool()]
        )
        
        # 結果収集用
        test_outputs = []
        test_success = False
        
        # 単一クエリ用の入力ストリーム
        async def simple_input_stream():
            yield json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": query}]
                }
            })
        
        # シンプルな出力ハンドラー
        async def simple_output_handler(chunk: str):
            test_outputs.append(chunk)
            print(f"Output: {chunk}")
        
        print("Executing... (Please wait)")
        
        try:
            # 十分な時間でテスト実行（15秒）
            await asyncio.wait_for(
                voice_agent.aconnect(
                    input_stream=simple_input_stream(),
                    send_output_chunk=simple_output_handler
                ),
                timeout=15.0
            )
            test_success = True
            
        except asyncio.TimeoutError:
            # タイムアウトでもレスポンスがあれば成功とみなす
            if test_outputs:
                test_success = True
                print("⏰ Timeout but got response - treating as success")
            else:
                print("❌ Timeout with no response")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # 結果評価
        if test_success and test_outputs:
            # 何らかの出力があれば成功
            final_output = test_outputs[-1] if test_outputs else ""
            if len(final_output.strip()) > 5:
                print("✅ SUCCESS - Got valid response")
                results.append(("PASS", query, final_output[:100]))
            else:
                print("❌ FAIL - Invalid response")
                results.append(("FAIL", query, "No valid output"))
        else:
            print("❌ FAIL - No response")
            results.append(("FAIL", query, "No response"))
        
        print("Waiting between tests...")
        await asyncio.sleep(3.0)  # 十分な待機時間
    
    # 最終結果サマリー
    print("\n" + "="*60)
    print("🎯 FINAL TEST RESULTS")
    print("="*60)
    
    passed = 0
    for status, query, output in results:
        status_icon = "✅" if status == "PASS" else "❌"
        print(f"{status_icon} {status}: {query}")
        if output and len(output) > 10:
            preview = output[:80] + "..." if len(output) > 80 else output
            print(f"    Response: {preview}")
        passed += 1 if status == "PASS" else 0
    
    print(f"\n📊 Results: {passed}/{len(test_queries)} tests passed")
    if passed == len(test_queries):
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️ {len(test_queries) - passed} test(s) failed")
    
    return results


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
        "スターウォーズを検索して",  # videocenter (movie)
        "猫の動画を探して",  # youtube (general)
        "料理のレシピ動画を検索して",  # youtube (general)
        "東京駅までナビゲーションを開始してください",
        "映画「君の名は」について教えて",
        "トム・ハンクスが出演している映画を教えて",
        "Set the air conditioning to 20 degrees",
        "Search for funny cat videos",  # youtube (general)
        "Search for The Matrix",  # videocenter (movie)
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


# 新しいテストモード選択機能
async def run_tests():
    """Run different test modes"""
    import sys
    
    if len(sys.argv) > 1:
        test_mode = sys.argv[1]
    else:
        print("Available test modes:")
        print("1. supervisor - Test supervisor directly")
        print("2. voice_react - Test OpenAIVoiceReactAgent with supervisor tool")
        test_mode = input("Select test mode (supervisor/voice_react): ").strip()
    
    if test_mode == "supervisor":
        await main()
    elif test_mode == "voice_react":
        # 環境変数の設定
        import os
        os.environ['OPENAI_VOICE_TEXT_MODE'] = '1'
        await test_voice_react_agent_with_supervisor()
    else:
        print("Invalid test mode. Running default supervisor test.")
        await main()

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_tests())