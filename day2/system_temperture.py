# adding libaries in the system to work
import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# call of the api key to work and make response
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# if api key is not found by any error message api not found
if not GROQ_API_KEY:
    raise ValueError("API key kaha hai bhai")

# you are creating your self to ask question from llm
client = Groq(api_key=GROQ_API_KEY)

# model is deside here and it should be perfectly named
# we can message the content that we want to ask to llm in the prompt section
# message me role and content
model = "llama-3.3-70b-versatile"
role = "user"
prompt = "i love you"

# set the system to behive
message_system ={
    "role":"system",
    "content": "you are my strict office manger and collegue"
}
message = {
    "role": role,
    "content": prompt
}

# the role and content is describe here
messages = [message_system,message]


# answer comes from the response section
# set the temp. to {0,2}
response = client.chat.completions.create(model=model, messages=messages, temperature=1)
#print(response)

print("#######################################")

answer = response.choices[0].message.content
print(answer)
