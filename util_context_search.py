import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_community.retrievers import TavilySearchAPIRetriever
from langchain_core.runnables import RunnableSequence
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

# 🔹 検索キーワード生成プロンプト
keyword_prompt = PromptTemplate.from_template("""
以下の曖昧なストーリーから、映画やテレビ番組を検索するための日本語キーワードを5〜8語で生成してください。

目的は、似たようなテーマ・ジャンル・キャラクター・設定・雰囲気を持つ映像作品を見つけることです。

ストーリー: 「{user_input}」

出力形式: スペース区切り（例: SF 近未来 ロボット 人間ドラマ アクション 感動 テレビシリーズ）
""")
keyword_chain: RunnableSequence = keyword_prompt | llm

# 🔹 検索結果からベストな作品を評価するプロンプト
ranking_prompt = PromptTemplate.from_template("""
Given the user's desired story theme below, evaluate the following candidate works.

User's story idea:
"{user_input}"

From the provided candidates, identify the works that best match the theme. Rank them from most to least relevant and return your output as a **pure JSON array**. Each item must follow this format:
{{
    "title": "<Exact title of the work>",
    "description": "<Brief summary of the work>",
    "reason": "<Why this work matches the user's input>"
}}

Requirements:
- "title" should be the exact title of the work as mentioned in the candidate text.
- "description" should concisely summarize the plot or setting.
- "reason" should clearly explain the match to the user's story idea.
- Return only valid JSON. Do NOT use markdown formatting like ```json.
- Do not include any extra text or explanation before or after the JSON.
- Please select only **one** work from the candidates.

Candidates:
{search_results}
""")
ranking_chain: RunnableSequence = ranking_prompt | llm

# 🔹 Tavily 検索
retriever = TavilySearchAPIRetriever(k=5)


def find_best_content(user_input: str) -> str:
    """ストーリー記述に基づき、TavilyとGPTでコンテンツを推薦する。"""
    # 1. キーワード生成
    keyword_response = keyword_chain.invoke({"user_input": user_input})
    keywords = keyword_response.content.strip()
    print(f"\n🔍 GPTが生成した検索キーワード: {keywords}")

    # 2. Tavily検索
    docs = retriever.invoke(keywords)
    if not docs:
        return "❌ Web検索結果が見つかりませんでした。"

    # 3. 結果整形
    print(f"\n🌐 Web検索結果（{len(docs)}件）:")
    candidates = ""
    for doc in docs:
        title = doc.metadata.get("title", "No Title")
        snippet = doc.page_content.strip().replace("\n", "")
        print(f"・{title}: {snippet[:60]}...")
        candidates += f"{title}: {snippet}\n"

    # 4. 評価・推薦
    ranking_response = ranking_chain.invoke({
        "user_input": user_input,
        "search_results": candidates
    })

    print("\n✅ GPTによる検索結果の評価:\n")
    response_content = ranking_response.content.strip()

    try:
        # JSONとしてパースを試みる
        json_response = json.loads(response_content)
        #json_response.append({
        #    "return_direct": True,
        #})
        json_response_str = json.dumps(json_response, indent=2, ensure_ascii=False)
        print(json_response_str)
        return json_response_str
    except json.JSONDecodeError as e:
        # パース失敗時のログとエラー内容を表示
        print("❌ JSONのパースに失敗しました。以下の内容を確認してください。")
        print(f"エラー内容: {str(e)}")
        print("受け取った文字列:")
        print(response_content)
        return {
            "error": "JSON parsing failed",
            "message": str(e),
            "raw_content": response_content
        }


def main():
    print("🔎 ストーリーの雰囲気・内容を入力してください（例: 勇者が魔王を倒して物語が始まる...）")
    user_input = "勇者が魔王を倒したところから物語がはじまる。エルフが自分探しのたびに出る"
    result = find_best_content(user_input)


if __name__ == "__main__":
    main()
