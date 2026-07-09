# adding libaries in the system to work 
import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

#call of the api key to work and make response 
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# if api key is not found by any error message api not found 
if not GROQ_API_KEY:
    raise ValueError("API key kaha hai bhai")

#you are creating your self to ask question from llm
client = Groq(api_key=GROQ_API_KEY)

#model is deside here and it should be perfectly named 
model = "llama-3.3-70b-versatile"
role = "user"
prompt = "Do you know Padho with Pratyush" # we can message the content that we want to ask to llm in the prompt section 
# message me role and content
message = {
    "role": role,
    "content": prompt
}

# the role and content is describe here 
messages = [message]


# answer comes from the response section 
response = client.chat.completions.create(model=model, messages=messages)
print(response)

print("#######################################")

answer = response.choices[0].message.content
print(answer)
