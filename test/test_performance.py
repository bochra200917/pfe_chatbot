#test/test_performance.py
import time
import requests

url = "http://localhost:8000/ask"

start = time.time()

r = requests.post(
    url,
    json={"question": "factures non payées"},
    auth=("admin", "secret")
)

end = time.time()

print("Response:", r.json())
print("Time:", end-start)