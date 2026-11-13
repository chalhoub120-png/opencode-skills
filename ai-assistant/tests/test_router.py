"""Smoke tests for the task router classification."""

from __future__ import annotations

from orchestrator.router import TaskClassifier, TaskType


def test_coding_classification():
    classifier = TaskClassifier()
    task, conf = classifier.classify("اكتب دالة بايثون لفرز قائمة", "ar", {})
    assert task == TaskType.CODING
    assert conf > 0


def test_reasoning_classification():
    classifier = TaskClassifier()
    task, conf = classifier.classify("حل المشكلة paso a paso", "ar", {})
    assert task == TaskType.REASONING
    assert conf > 0


def test_general_classification():
    classifier = TaskClassifier()
    task, conf = classifier.classify("مرحبا كيفك", "ar", {})
    assert task == TaskType.GENERAL
    assert conf > 0


def test_arabic_script_defaults_to_ar():
    classifier = TaskClassifier()
    task, conf = classifier.classify("ماذا تفعل", "ar", {})
    assert task in (TaskType.GENERAL, TaskType.REASONING)


def test_notification_intent_requires_automation_classification():
    assert (
        TaskClassifier.is_notification_request(
            "أرسل إشعار عبر الإيميل", TaskType.AUTOMATION
        )
        is True
    )


def test_notification_intent_ignored_for_other_task_types():
    assert (
        TaskClassifier.is_notification_request("أرسل إشعار", TaskType.GENERAL) is False
    )


def test_automation_question_is_not_a_notification_request():
    classifier = TaskClassifier()
    message = "ما هو webhook وكيف يعمل؟"
    task, _ = classifier.classify(message, "ar", {})
    assert task == TaskType.AUTOMATION
    assert classifier.is_notification_request(message, task) is False


def test_end_to_end_intent_detection():
    classifier = TaskClassifier()
    message = "سجّل تنبيه في قاعدة البيانات للاجتماع القادم"
    task, _ = classifier.classify(message, "ar", {})
    assert task == TaskType.AUTOMATION
    assert classifier.is_notification_request(message, task) is True
