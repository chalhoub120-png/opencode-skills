#!/usr/bin/env python3
"""HOST-HARDEN-01 Smart Assistant (Local Offline First)."""

import json, os, sys, subprocess
from pathlib import Path

# --- Project HOST-HARDEN-01: Offline Knowledge Base ---
PROJECT_CONTEXT = {
    "project": "HOST-HARDEN-01",
    "version": "2.0",
    "date": "2026-11-10",
    "owner": "مالك الجهاز",
    "deliverables": {
        "docx": "HOST-HARDEN-01-Report.docx",
        "xlsx": "HOST-HARDEN-01-Data.xlsx",
        "pptx": "HOST-HARDEN-01-Deck.pptx",
        "pdf": "HOST-HARDEN-01-Report.pdf",
    },
    "checklist_p0": [
        ("نسخة WSL2 مصدّرة", False),
        ("نسخة Dify + postgres", False),
        ("تمرين استرجاع في توزيعة تجريبية", False),
        ("nginx يستمع على 127.0.0.1", False),
        ("plugin_daemon يستمع على 127.0.0.1", False),
        ("اختبار من هاتف يفشل", False),
        ("صلاحيّة كل .env = 600", False),
        ("تدوير المفاتيح", False),
        ("PUA=1 و NP=1 و CFA=1..2", False),
        ("6 قواعد ASR على الأقل", False),
        ("BitLocker مؤكد مفعّل", True),  # #11 marked ✅
        ("سجل الاستثناءات", False),
        ("لوحة القيادة خضراء", False),
    ],
    "open_questions": {
        "O1": "BitLocker: assumption (credentials changed)",
        "O5": "نوع الشبكة: خاصة",
    },
    "decisions_d1_d7": {
        "D1": "Defender وحده، لا AVG",
        "D2": "لا beam search في Ollama",
        "D3": "رفض gVisor/Kata/Terraform/SIEM/WAF",
        "D4": "Loopback-first",
        "D5": "نسخ احتياطي قبل التحصين",
        "D6": "لا أوامر تدميرية بلا تأكيد",
        "D7": "نقل claude-api إلى _disabled",
    },
}


def ask_assistant(question, context=None):
    """Try Ollama first, fallback to rules-based knowledge base."""
    # Attempt Ollama
    try:
        prompt = f"""سياق المشروع:\n{json.dumps(PROJECT_CONTEXT, ensure_ascii=False, indent=2)}\n\nالسؤال: {question}\nاجب بناءً على السياق فقط.\n\nuser: {question}\nassistant:"""
        result = subprocess.run(
            ["ollama", "run", "llama3"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # Fallback: rules based on knowledge base
    q = question.lower()
    if "bitlocker" in q or "bitlocker" in q:
        return "✅ BitLocker: assumption enabled (based on credential change & single-user device)."
    if "type of network" in q or "network type" in q or "O5" in q:
        return "نوع الشبكة: خاصة (Private)."
    if "checklist" in q or "P0" in q:
        return "قائمة تحقق P0 بها 13 بنداً، #11 BitLocker ✅، البقية ☐ للتعبئة اليدوية."
    if "deliverable" in q or "file" in q:
        return f"المخرجات: {list(PROJECT_CONTEXT['deliverables'].values())}"
    if "decision" in q or "D1" in q or "D7" in q:
        return list(PROJECT_CONTEXT["decisions_d1_d7"].values())[0]
    return "لا أعرف من السياق، لكن يمكنني البحث في ملفات المشروع إذا أضفت السياق."


def main():
    print("=== مساعد HOST-HARDEN-01 الذكي (محلي/offline) ===")
    print(f"المشروع: {PROJECT_CONTEXT['project']} {PROJECT_CONTEXT['version']}")
    print("اكتب سؤالك، أو 'exit' للخروج.\n")
    while True:
        try:
            q = input("\nسؤالك: ").strip()
        except EOFError:
            break
        if q.lower() in ("exit", "quit", "q"):
            print("إلى اللقاء!")
            break
        if not q:
            continue
        answer = ask_assistant(q)
        print(f"\nمساعد: {answer}\n")


if __name__ == "__main__":
    main()
