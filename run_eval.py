#!/usr/bin/env python3
"""Eval: eval_questions.json ke sawal assistant se poochkar sahi-galat ginta hai.

Chalane ka tareeka:   python3 run_eval.py
Ye eval_results.json banata hai, aur dashboard ka 'Eval accuracy' apne aap bhar jata hai.
"""
import json
import time

import llm
import notes
from config import EVAL_QUESTIONS_FILE, EVAL_RESULTS_FILE

PLACEHOLDER = "FILL"  # jab tak keyword 'FILL' hai, sawal gina nahi jayega


def ask_model(question):
    # Bilkul wahi flow jo dashboard aur assistant mein hota hai: translit -> search_best -> prompt -> jawab.
    # (Pehle ye seedha search() naapta tha, jo asli raasta nahi hai: wahi sawal 34/46 vs 42/46 nikalta tha.)
    import translit
    passages = notes.INDEX.search_best([translit.to_roman(question)])
    reply = llm.chat([{"role": "user", "content": notes.build_prompt(question, passages)}])
    return reply["content"], passages


def is_ready(case):
    if case.get("unanswerable"):
        return True
    words = case.get("expect_any", [])
    return bool(words) and PLACEHOLDER not in words


def passes(case, answer):
    # Notes mein jo nahi hai uspar "I don't know" sahi hai; jo hai uspar koi keyword milna chahiye.
    if case.get("unanswerable"):
        return notes.is_dont_know(answer)
    return any(word.lower() in answer.lower() for word in case["expect_any"])


def main():
    cases = json.loads(EVAL_QUESTIONS_FILE.read_text(encoding="utf-8"))
    notes.INDEX.build()
    correct = total = 0
    for case in cases:
        question = case["question"]
        if not is_ready(case):
            print(f"SKIP  {question}   (expect_any mein file se keyword bharo)")
            continue
        answer, passages = ask_model(question)
        ok = passes(case, answer)
        total += 1
        correct += int(ok)
        score, chunk = passages[0]
        print(f"{'PASS' if ok else 'FAIL'}  {question}   [best: {chunk['source']} {score:.2f}]")
        if not ok:
            print(f"      AI ne kaha: {answer[:160]!r}")
    if total == 0:
        print("Abhi koi sawal ready nahi hai. Pehle expect_any mein keywords bharo.")
        return
    summary = {"correct": correct, "total": total, "ran_at": time.strftime("%Y-%m-%d %H:%M")}
    EVAL_RESULTS_FILE.write_text(json.dumps(summary), encoding="utf-8")
    print(f"\nScore: {correct} of {total} ({round(100 * correct / total)}%). Dashboard refresh karo.")


if __name__ == "__main__":
    try:
        main()
    except OSError:
        print("Ollama se connect nahi ho paya. Ollama app kholo aur dobara chalao.")
