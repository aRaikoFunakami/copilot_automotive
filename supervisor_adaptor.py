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

# ユーザー入力を抽出する関数
def extract_user_input_multiple_patterns(input_data):
    """input_data からユーザー入力を抽出する関数"""
    messages = input_data.get("messages", [])
    for message in reversed(messages):
        # メッセージが辞書型の場合
        if isinstance(message, dict) and message.get("role") == "user":
            return message.get("content", "")
        # メッセージがLangChainのHumanMessageクラスの場合
        elif hasattr(message, "content") and type(message).__name__ == "HumanMessage":
            return message.content
        # メッセージがクラス型でrole属性がある場合
        elif hasattr(message, "role") and hasattr(message, "content"):
            # HumanMessageの場合、roleは通常"human"または"user"
            if message.role in ["user", "human"]:
                return message.content
    
    # デバッグ情報を追加
    print("=== Extract Debug ===")
    for i, message in enumerate(messages):
        print(f"Message {i}: {type(message)}")
        if hasattr(message, "role"):
            print(f"  Role: {message.role}")
        if hasattr(message, "content"):
            print(f"  Content: {message.content}")
        print(f"  Type name: {type(message).__name__}")
    
    raise ValueError("ユーザー入力が見つかりません")