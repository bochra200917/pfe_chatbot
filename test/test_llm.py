# test/test_llm.py
from app.llm_client import call_llm

prompt = "What is the capital of France?"

response = call_llm(prompt)

print(response)