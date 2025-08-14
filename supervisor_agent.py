
import sys
import os
from langgraph_supervisor import create_supervisor
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI
from realtime_tools import TOOLS


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../tmdb_agent")))
from tmdb_agent.agent import create_tmdb_agent




# 既存のAgentExecutorをsupervisor用に変換する関数
def adapt_agent_executor_for_supervisor(agent_executor, name, debug=False):
    """Unify normal/debug behavior:
    - Always extract user input via extract_user_input_multiple_patterns
    - Emit detailed debug logs only when debug=True
    """
    def supervisor_compatible_agent(input_data, config=None):
        """Supervisor-compatible agent wrapper"""
        try:
            # Debug: high-level shape
            if debug:
                print("=== TMDB Agent Debug Info ===")
                print(f"Input data keys: {list(input_data.keys())}")
                print(f"Input data type: {type(input_data)}")
                if "messages" in input_data:
                    messages_dbg = input_data["messages"]
                    print(f"Messages count: {len(messages_dbg)}")
                    print(f"Messages type: {type(messages_dbg)}")
                    for i, msg in enumerate(messages_dbg):
                        print(f"Message {i}: {type(msg)}")
                        if isinstance(msg, dict):
                            print(f"  - Keys: {list(msg.keys())}")
                            print(f"  - Role: {msg.get('role', 'N/A')}")
                            # Preview up to 100 chars
                            print(f"  - Content preview: {str(msg.get('content', 'N/A'))[:100]}")
                        else:
                            # Generic object preview
                            preview = getattr(msg, "content", str(msg))
                            print(f"  - Role: {getattr(msg, 'role', 'N/A')}")
                            print(f"  - Content preview: {str(preview)[:100]}")
                else:
                    print("No 'messages' key found")
                    print(f"Available keys: {list(input_data.keys())}")
                print("================================")

            # Always use the robust extractor
            user_input = extract_user_input_multiple_patterns(input_data)

            if not user_input:
                if debug:
                    print("=== Extended Debug: Full Input Data ===")
                    print(f"Full input_data: {input_data}")
                raise ValueError("ユーザー入力が見つかりません")

            if debug:
                print(f"抽出されたユーザー入力: {user_input}")

            # Invoke wrapped AgentExecutor
            result = agent_executor.invoke({"input": user_input})
            output = result.get("output", "検索結果を取得できませんでした")

            if debug:
                # Trim preview to avoid huge console output
                print(f"TMDB結果: {str(output)[:200]}...")

            # Return in supervisor message format
            messages = input_data.get("messages", [])
            updated_messages = messages + [{
                "role": "assistant",
                "content": output,
                "name": name
            }]

            return {**input_data, "messages": updated_messages}

        except Exception as e:
            # Error logging
            if debug:
                print(f"TMDBエージェントエラー: {str(e)}")
                import traceback
                traceback.print_exc()

            error_message = f"エラーが発生しました: {str(e)}"
            messages = input_data.get("messages", [])
            updated_messages = messages + [{
                "role": "assistant",
                "content": error_message,
                "name": name,
                "metadata": {"error": True}
            }]
            return {**input_data, "messages": updated_messages}

    # Provide name attribute and .invoke alias for supervisor
    supervisor_compatible_agent.name = name
    supervisor_compatible_agent.invoke = supervisor_compatible_agent
    return supervisor_compatible_agent


# TMDBエージェントの初期化
tmdb_agent = create_tmdb_agent(
    llm=ChatOpenAI(model="gpt-4.1-mini", temperature=0.1),
    verbose=True,
)

# アダプターを適用
tmdb_supervisor_compatible = adapt_agent_executor_for_supervisor(
    agent_executor=tmdb_agent.agent_executor,
    name="tmdb_search_agent"
)


supervisor = create_supervisor(
    model=init_chat_model("openai:gpt-4.1-mini"),
    agents=[
        TOOLS,
        tmdb_supervisor_compatible,  # TMDBエージェントを追加
    ],
    prompt=(
        "You are a supervisor managing three agents:\n"
        "- TMDBSearchAgent: Handles movie, TV show, and celebrity information searches using TMDB API. "
        "Supports multilingual queries and can search for cast/crew information, plot details, release dates, ratings, etc.\n\n"
        
        "ASSIGNMENT RULES:\n"
        "1. Assign work to ONE agent at a time - do not call agents in parallel.\n"
        "2. Do not perform any work yourself - always delegate to appropriate agents.\n"
        "3. For movie/TV/celebrity queries: Use TMDBSearchAgent for any entertainment content questions.\n\n"
        
        "TASK ROUTING:\n"
        "- Movie/TV show information (plot, cast, release date, ratings) → TMDBSearchAgent\n"
        "- Celebrity/actor/director information → TMDBSearchAgent\n"
        "- Entertainment industry questions → TMDBSearchAgent\n"
        
        "COMPLEX TASKS:\n"
        "1. Use TMDBSearchAgent if entertainment content is involved\n\n"
        
        "Always respond in the same language as the user's query."
    ),
    add_handoff_back_messages=True,
    output_mode="full_history",
).compile()



# Supervisorをツールとして使用するための関数
@tool("supervisor_agent", description="Handles complex tasks requiring arithmetic operations, unit conversions, or movie/TV/celebrity information searches. Use this tool for mathematical calculations, unit conversions, or entertainment content queries.")
def supervisor_tool(query: str) -> str:
    """
    Supervisorエージェントを呼び出すツール
    Args:
        query: ユーザーのクエリ（計算、単位変換、映画・TV番組情報検索など）
    Returns:
        処理結果の文字列
    """
    try:
        print(f"Supervisor tool called with query: {query}")
        
        # Supervisorに送信
        result_messages = []
        for chunk in supervisor.stream({
            "messages": [{"role": "user", "content": query}]
        }):
            for node_name, node_update in chunk.items():
                messages = convert_to_messages(node_update["messages"])
                if messages:
                    result_messages.extend(messages)
        
        # 最後のアシスタントメッセージを取得
        for message in reversed(result_messages):
            if hasattr(message, 'content') and message.content:
                # assistantまたはエージェント名付きのメッセージを探す
                if (hasattr(message, 'role') and message.role == 'assistant') or \
                   (hasattr(message, 'name') and message.name in ['ArithmeticAgent', 'UnitConversionAgent', 'tmdb_search_agent']):
                    return message.content
        
        return "申し訳ありませんが、処理できませんでした。"
    
    except Exception as e:
        print(f"Supervisor tool error: {str(e)}")
        return f"エラーが発生しました: {str(e)}"