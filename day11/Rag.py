import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
my_api_key = os.getenv("GROQ_API_KEY")

if not my_api_key:
    raise ValueError("API key kaha hai bhai")

client = Groq(api_key=my_api_key)
model = "llama-3.3-70b-versatile"


# step 1
knowledge_base = {
    "transformer architecture": "The Transformer architecture was introduced in 2017 by Vaswani et al. in the paper 'Attention Is All You Need'.",
    "chatgpt": "ChatGPT is a conversational AI model based on OpenAI's GPT architecture and first launched in November 2022.",
    "llama": "LLaMA is a family of foundation language models released by Meta AI in 2023."
}

# step 2 retrieval

def retrieve_info(question):
    question = question.lower()
    if "transformer" in question or "attention is all you need" in question:
        return knowledge_base["transformer architecture"]
    elif "chatgpt" in question:
        return knowledge_base["chatgpt"]
    elif "llama" in question or "meta ai" in question:
        return knowledge_base["llama"]
    else:
        return None


def ask_llm(question):
    context = retrieve_info(question)

    sys_prompt = f"""Answer in one line only. Answer only based on this context. Do not hallucinate. Context: {context}"""
    system_message = {
        "role": "system",
        "content": sys_prompt

    }
    message = {
        "role": "user",
        "content": question
    }
    messages = [system_message, message]
    response = client.chat.completions.create(model=model, messages=messages)
    answer = response.choices[0].message.content
    return answer


question = "When was the Transformer architecture introduced?"
print(ask_llm(question))
