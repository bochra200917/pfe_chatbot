# test/test_golden_set.py
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.chatbot import match_question, get_response


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def load_golden_set(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_golden_set(tests):
    total = len(tests)
    success = 0
    failures = []

    for test in tests:
        question = test["question"]
        try:
            if "expected_template" in test:
                template, params = match_question(question)
                if template == test["expected_template"] and params == test["expected_params"]:
                    success += 1
                else:
                    failures.append({
                        "question": question,
                        "expected": f"{test['expected_template']} {test['expected_params']}",
                        "got": f"{template} {params}"
                    })

            else:
                result = get_response(question)
                status = result.get("metadata", {}).get("status")
                template = result.get("metadata", {}).get("template")

                if test.get("expected_reject"):
                    if status == "rejected":
                        success += 1
                    else:
                        failures.append({"question": question, "expected": "rejected", "got": status})

                elif test.get("expected_clarification"):
                    if status == "clarification_required":
                        success += 1
                    else:
                        failures.append({"question": question, "expected": "clarification_required", "got": status})

                else:
                    if template == test.get("expected_intent"):
                        success += 1
                    else:
                        failures.append({"question": question, "expected": test.get("expected_intent"), "got": template})

        except Exception as e:
            failures.append({"question": question, "error": str(e)})

    return total, success, failures


# ─────────────────────────────────────────────────────────────
# Tests V1
# ─────────────────────────────────────────────────────────────

def test_golden_set_v1_accuracy():
    """Golden set V1 — accuracy 100%"""
    tests = load_golden_set("golden_set.json")
    total, success, failures = run_golden_set(tests)
    accuracy = (success / total) * 100
    print(f"\nV1 : {success}/{total} = {accuracy:.2f}%")
    for f in failures:
        print(f"  ❌ {f}")
    assert accuracy == 100.0, f"V1 accuracy {accuracy:.2f}% < 100%"


# ─────────────────────────────────────────────────────────────
# Tests V2
# ─────────────────────────────────────────────────────────────

def test_golden_set_v2_accuracy():
    """Golden set V2 — accuracy 100%"""
    tests = load_golden_set("golden_set_v2.json")
    total, success, failures = run_golden_set(tests)
    accuracy = (success / total) * 100
    print(f"\nV2 : {success}/{total} = {accuracy:.2f}%")
    for f in failures:
        print(f"  ❌ {f}")
    assert accuracy == 100.0, f"V2 accuracy {accuracy:.2f}% < 100%"


# ─────────────────────────────────────────────────────────────
# Tests V3
# ─────────────────────────────────────────────────────────────

def test_golden_set_v3_accuracy():
    """Golden set V3 — accuracy 100%"""
    tests = load_golden_set("golden_set_v3.json")
    total, success, failures = run_golden_set(tests)
    accuracy = (success / total) * 100
    print(f"\nV3 : {success}/{total} = {accuracy:.2f}%")
    for f in failures:
        print(f"  ❌ {f}")
    assert accuracy == 100.0, f"V3 accuracy {accuracy:.2f}% < 100%"


# ─────────────────────────────────────────────────────────────
# Tests V3 étendu (60 questions)
# ─────────────────────────────────────────────────────────────

def test_golden_set_v3_extended_accuracy():
    """Golden set V3 étendu 60 questions — accuracy 100%"""
    tests = load_golden_set("golden_set/golden_set_v3_extended.json")
    total, success, failures = run_golden_set(tests)
    accuracy = (success / total) * 100
    print(f"\nV3 étendu : {success}/{total} = {accuracy:.2f}%")
    for f in failures:
        print(f"  ❌ {f}")
    assert accuracy == 100.0, f"V3 étendu accuracy {accuracy:.2f}% < 100%"


# ─────────────────────────────────────────────────────────────
# Tests sécurité spécifiques
# ─────────────────────────────────────────────────────────────

def test_all_injections_rejected():
    """Toutes les tentatives d'injection doivent être rejetées"""
    tests = load_golden_set("golden_set/golden_set_v3_extended.json")
    injections = [t for t in tests if t.get("expected_reject")]

    failed = []
    for test in injections:
        result = get_response(test["question"])
        status = result.get("metadata", {}).get("status")
        if status != "rejected":
            failed.append({"question": test["question"], "got": status})

    print(f"\nInjections : {len(injections) - len(failed)}/{len(injections)} rejetées")
    assert len(failed) == 0, f"Injections non rejetées : {failed}"


def test_all_clarifications_returned():
    """Toutes les questions ambiguës doivent retourner clarification_required"""
    tests = load_golden_set("golden_set/golden_set_v3_extended.json")
    clarifications = [t for t in tests if t.get("expected_clarification")]

    failed = []
    for test in clarifications:
        result = get_response(test["question"])
        status = result.get("metadata", {}).get("status")
        if status != "clarification_required":
            failed.append({"question": test["question"], "got": status})

    print(f"\nClarifications : {len(clarifications) - len(failed)}/{len(clarifications)} correctes")
    assert len(failed) == 0, f"Clarifications manquées : {failed}"