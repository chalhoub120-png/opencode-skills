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


def test_explicit_notification_request_is_detected():
    assert (
        TaskClassifier.is_notification_request(
            "أرسل إشعار عبر الإيميل", TaskType.AUTOMATION
        )
        is True
    )


def test_notification_intent_does_not_require_automation_classification():
    # Real requests are classified GENERAL; gating on AUTOMATION dropped them.
    assert (
        TaskClassifier.is_notification_request("أرسل إشعار", TaskType.GENERAL) is True
    )


def test_reminder_phrase_is_a_notification_request():
    classifier = TaskClassifier()
    message = "ذكّرني بالاجتماع غدًا"
    task, _ = classifier.classify(message, "ar", {})
    assert task == TaskType.GENERAL
    assert classifier.is_notification_request(message, task) is True


def test_question_about_sending_a_notification_is_not_a_request():
    assert TaskClassifier.is_notification_request("كيف أرسل إشعارًا؟") is False


def test_notification_noun_alone_is_not_a_request():
    assert TaskClassifier.is_notification_request("الإشعارات مهمة جدًا") is False


def test_english_notification_request_is_detected():
    assert TaskClassifier.is_notification_request("send me an alert tomorrow") is True


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
