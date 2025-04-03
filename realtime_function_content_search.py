import asyncio
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from util_context_search import find_best_content
from typing import Any, Optional, Type

from langchain.prompts import PromptTemplate
refine_prompt = PromptTemplate.from_template("""
Please introduction in natural Japanese based on its title, description, and reason.

【Constraints】
- The output must be exactly **one sentence only**, with only **one period** (".") used.
- Use the title **exactly as it is**, without modifying its spelling or wording (e.g., "{title}").
- Do **not** use Markdown formatting (e.g., **bold**, lists, etc.).
- Avoid decorative or non-standard characters (e.g., ★, ●, ※, emoji, etc.).
- The sentence should be concise, engaging, and easy to read in spoken English.
- Do not include multiple works or multiple recommendations—focus on only **one** work.

【Video Candidates】
title: {title}
description: {description}
reason: {reason}

【Output】
- A natural, single-sentence introduction including the selected title, with no special formatting.
""")



class FindBestContentToolInput(BaseModel):
    user_input: str = Field(
        description="""
        "Given a user input story"
        """
    )


class FindBestContentTool(BaseTool):
    """LangChain tool that wraps the 'find_best_content' function."""
    # Add type annotations for name, description
    name: str = "find_best_content"
    description: str = (
        "Given a user input story, returns recommended content from Tavily search."
        "The input should be a brief story or scenario in Japanese."
    )
    args_schema: Type[BaseModel] = FindBestContentToolInput
    return_direct: bool = True

    def _run(self, user_input: str) -> str:
        """Synchronous execution."""
        # return find_best_content(user_input)
        result = find_best_content(refine_prompt)
        refine_prompt.format(title = result[0]['title'], description = result[0]['description'],reason = result[0]['reason'])
        return result

    async def _arun(self, user_input: str) -> str:
        """Asynchronous execution using asyncio."""
        return await asyncio.to_thread(find_best_content, user_input)




async def main():
    tool = FindBestContentTool()
    result = await tool.arun("もう少しシリアスでダークな展開が欲しい")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
