# https://platform.openai.com/docs/guides/tools-web-search?api-mode=responses
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-4o",
    tools=[{"type": "web_search_preview"}],
    input="今の日本の総理大臣は？?Please respond in natural, spoken language as if the answer is meant to be read aloud. answer in Japanese"
)

print(response.output_text)