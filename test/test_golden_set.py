import json
from app.chatbot import match_question
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
def run_tests(golden_file):
    with open(golden_file, "r", encoding="utf-8") as f:
        tests = json.load(f)

    total = len(tests)
    success = 0

    for i, test in enumerate(tests, 1):
        question = test["question"]
        expected_template = test["expected_template"]
        expected_params = test["expected_params"]

        try:
            template, params = match_question(question)

            template_ok = template == expected_template
            params_ok = params == expected_params

            if template_ok and params_ok:
                print(f"✅ Test {i} OK")
                success += 1
            else:
                print(f"❌ Test {i} FAILED")
                print(f"   Question: {question}")
                print(f"   Expected: {expected_template} {expected_params}")
                print(f"   Got: {template} {params}")

        except Exception as e:
            print(f"❌ Test {i} ERROR: {str(e)}")

    accuracy = (success / total) * 100
    print("\n==========================")
    print(f"Total tests: {total}")
    print(f"Passed: {success}")
    print(f"Accuracy: {accuracy:.2f}%")
    print("==========================")

if __name__ == "__main__":
    print("Running V1 Golden Set")
    run_tests("test/golden_set.json")

    print("\nRunning V2 Golden Set")
    run_tests("test/golden_set_v2.json")