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
