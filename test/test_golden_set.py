# test/test_golden_set.py
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.chatbot import match_question, get_response

def run_tests(golden_file):

    with open(golden_file, "r", encoding="utf-8") as f:
        tests = json.load(f)

    total = len(tests)
    success = 0

    for i, test in enumerate(tests, 1):

        question = test["question"]

        try:

            if "expected_template" in test:

                template, params = match_question(question)

                template_ok = template == test["expected_template"]
                params_ok = params == test["expected_params"]

                if template_ok and params_ok:
                    print(f"✅ Test {i} OK")
                    success += 1
                else:
                    print(f"❌ Test {i} FAILED")
                    print(f"   Question: {question}")
                    print(f"   Expected: {test['expected_template']} {test['expected_params']}")
                    print(f"   Got: {template} {params}")

            else:

                result = get_response(question)
                metadata = result.get("metadata", {})

                status = metadata.get("status")
                template = metadata.get("template")

                if test.get("expected_reject"):

                    if status == "rejected":
                        print(f"✅ Test {i} Reject OK")
                        success += 1
                    else:
                        print(f"❌ Test {i} Reject FAILED")
                        print(f"   Question: {question}")
                        print(f"   Expected: rejected")
                        print(f"   Got: {status}")

                elif test.get("expected_clarification"):

                    if status == "clarification_required":
                        print(f"✅ Test {i} Clarification OK")
                        success += 1
                    else:
                        print(f"❌ Test {i} Clarification FAILED")
                        print(f"   Question: {question}")
                        print(f"   Expected: clarification_required")
                        print(f"   Got: {status}")

                else:

                    if template == test["expected_intent"]:
                        print(f"✅ Test {i} Intent OK")
                        success += 1
                    else:
                        print(f"❌ Test {i} Intent FAILED")
                        print(f"   Question: {question}")
                        print(f"   Expected: {test['expected_intent']}")
                        print(f"   Got: {template}")

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

    print("\nRunning V3 Golden Set")
    run_tests("test/golden_set_v3.json")