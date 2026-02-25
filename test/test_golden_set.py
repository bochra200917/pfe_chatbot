#test/test_golden_set.py
import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from app.chatbot import match_question

#golden_path = os.path.join(ROOT_DIR, "test", "golden_set.json")
golden_path = os.path.join(ROOT_DIR, "test", "golden_set_v2.json")

with open(golden_path, "r", encoding="utf-8") as f:
    data = json.load(f)

success = 0

print("=== TEST GOLDEN SET ===\n")

for item in data:
    question = item["question"]
    expected_template = item["expected_template"]
    expected_params = item["expected_params"]

    template_function, params = match_question(question)

    if template_function and \
       template_function.__name__ == expected_template and \
       params == expected_params:

        print(f"✅ OK : {question}")
        success += 1
    else:
        print(f"❌ ERREUR : {question}")
        if template_function:
            print("   → Template reçu :", template_function.__name__)
            print("   → Params reçus :", params)
        else:
            print("   → Question non reconnue")

print(f"\nRésultat final : {success}/{len(data)} correct")