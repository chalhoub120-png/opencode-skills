"""Security Threat Detection & Warning System.

Detects potential risks and attack attempts in real time, classifies each
threat by severity, and emits structured warnings that can be logged, alerted,
or surfaced to administrators.

Design notes (evidence-based):
- Patterns are high-confidence only, following OWASP WSTG (INJV) and the
  corresponding CWE classes: CWE-89 (SQLi), CWE-78 (OS command injection),
  CWE-22 (path traversal), CWE-79 (XSS), CWE-639 (IDOR).
- Natural-language payloads (chat/voice/knowledge) are NOT regex-scanned for
  SQL/command keywords: doing so blocks legitimate requests such as
  "select the best option" or a coding question containing "rm -rf".
  Structural attacks are still detected through query parameters and
  tool-boundary validation.
"""

from __future__ import annotations

import re
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Threat classification
# ---------------------------------------------------------------------------


@dataclass
class ThreatEvent:
    """A single detected threat with full context."""

    threat_id: str
    threat_type: str
    severity: str  # low, medium, high, critical
    user_id: Optional[str]
    ip_address: Optional[str]
    endpoint: str
    method: str
    description_ar: str
    description_en: str
    evidence: Dict[str, Any]
    detected_at: str
    recommended_action: str
    blocked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threat_id": self.threat_id,
            "threat_type": self.threat_type,
            "severity": self.severity,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "endpoint": self.endpoint,
            "method": self.method,
            "description_ar": self.description_ar,
            "description_en": self.description_en,
            "evidence": self.evidence,
            "detected_at": self.detected_at,
            "recommended_action": self.recommended_action,
            "blocked": self.blocked,
        }


# ---------------------------------------------------------------------------
# High-confidence detection patterns (compiled once)
# ---------------------------------------------------------------------------

# CWE-89: require SQL grammar, not a bare keyword.
_SQL_INJECTION = re.compile(
    r"("
    r"union\s+(all\s+)?select"
    r"|drop\s+(table|database|schema)"
    r"|truncate\s+table"
    r"|alter\s+table\s+\w+"
    r"|insert\s+into\s+\w+\s*\("
    r"|delete\s+from\s+\w+"
    r"|update\s+\w+\s+set\s+\w+\s*="
    r"|or\s+1\s*=\s*1"
    r"|'\s*or\s*'1'\s*=\s*'1"
    r";\s*--"
    r"|pg_sleep\s*\("
    r"|sleep\s*\(\s*\d+\s*\)"
    r"|benchmark\s*\("
    r"|information_schema"
    r"|waitfor\s+delay"
    r")",
    re.IGNORECASE,
)

# CWE-22: traversal sequences (raw and percent-encoded).
_PATH_TRAVERSAL = re.compile(
    r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|%252e%252e)",
    re.IGNORECASE,
)

# CWE-78: require command execution context, not a bare word like "format".
_COMMAND_INJECTION = re.compile(
    r"("
    r"\brm\s+-[rf]{1,2}\b"
    r"|\bcurl\s+https?://"
    r"|\bwget\s+https?://"
    r"|\bbash\s+-c\b"
    r"|\bsh\s+-c\b"
    r"|\bsudo\s+\w+"
    r"|\bchmod\s+[0-7]{3,4}\b"
    r"|\bchown\s+\w+"
    r"|\bpowershell(\.exe)?\s+-"
    r"|\bcmd(\.exe)?\s+/c\b"
    r"|\bnc\s+-[el]"
    r"|\bnetcat\s+-[el]"
    r"|\bpopen\s*\("
    r"|\bsystem\s*\("
    r"|\bexec\s*\("
    r"|\$\(\s*\w+"
    r"|`[^`]+`"
    r")",
    re.IGNORECASE,
)

# CWE-79: script execution context.
_XSS_PATTERN = re.compile(
    r"(<\s*script\b|javascript\s*:|onerror\s*=|onload\s*=|document\.cookie|"
    r"<\s*iframe\b|srcdoc\s*=)",
    re.IGNORECASE,
)

# Secrets / sensitive files that must never be reachable via parameters.
# `.env` is only matched at a path/assignment boundary, so words such as
# "environment" or "envelope" are not flagged.
_SENSITIVE_PATH = re.compile(
    r"(?:^|[=/\s\"'])\.env\b"
    r"|\.git[/\\]"
    r"|\bid_rsa\b"
    r"|/etc/passwd\b"
    r"|/etc/shadow\b"
    r"|\bcredentials\.json\b"
    r"|\bprivate[_-]?key\b",
    re.IGNORECASE,
)

# Endpoints that legitimately receive free-form natural language.
NATURAL_LANGUAGE_PREFIXES = (
    "/chat",
    "/voice",
    "/knowledge",
)


# ---------------------------------------------------------------------------
# Threat detector
# ---------------------------------------------------------------------------


class ThreatDetector:
    """Real-time threat detection for the AI Assistant API.

    Each worker keeps its own sliding windows (no shared mutable state across
    processes). Thresholds are configurable per deployment.
    """

    def __init__(self) -> None:
        self._ip_requests: Dict[str, deque[float]] = defaultdict(deque)
        self._user_requests: Dict[str, deque[float]] = defaultdict(deque)
        self._ip_failures: Dict[str, deque[float]] = defaultdict(deque)
        self._user_failures: Dict[str, deque[float]] = defaultdict(deque)
        self._totp_failures: Dict[str, deque[float]] = defaultdict(deque)

        self.rate_limit_window = 60.0  # seconds
        self.rate_limit_max = 120  # requests per window
        self.failure_window = 300.0  # seconds
        self.failure_max = 5  # failures per window
        self.totp_failure_max = 3  # TOTP failures per window

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> float:
        return time.time()

    @staticmethod
    def _iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _prune(self, dq: deque[float], window: float) -> None:
        cutoff = self._now() - window
        while dq and dq[0] < cutoff:
            dq.popleft()

    @staticmethod
    def _recommend(threat_type: str) -> str:
        recs: Dict[str, str] = {
            "sql_injection": "block the source IP and review parameterized queries",
            "path_traversal": "block IP and audit file-access logs",
            "command_injection": "block IP immediately; critical host risk",
            "xss_attempt": "block request and enforce output encoding",
            "brute_force_auth": "lock the account temporarily and require TOTP",
            "totp_brute_force": "lock TOTP for 15 minutes and notify the user",
            "idor_attempt": "deny access, review RBAC and object ownership",
            "sensitive_path_access": "deny access and rotate any exposed secrets",
            "rate_limit_abuse": "apply progressive delay or temporary block",
            "audit_tampering": "critical: preserve logs and investigate immediately",
            "privilege_escalation": "revoke elevated role and audit user actions",
        }
        return recs.get(threat_type, "Review the event and apply access control")

    def _threat(
        self,
        *,
        threat_type: str,
        severity: str,
        user_id: Optional[str],
        ip_address: Optional[str],
        endpoint: str,
        method: str,
        description_ar: str,
        description_en: str,
        evidence: Dict[str, Any],
        blocked: bool = False,
    ) -> ThreatEvent:
        return ThreatEvent(
            threat_id=f"threat-{uuid.uuid4().hex[:12]}",
            threat_type=threat_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            method=method,
            description_ar=description_ar,
            description_en=description_en,
            evidence=evidence,
            detected_at=self._iso(),
            recommended_action=self._recommend(threat_type),
            blocked=blocked,
        )

    # ------------------------------------------------------------------
    # Request inspection
    # ------------------------------------------------------------------

    def detect_request(
        self,
        *,
        user_id: Optional[str],
        ip_address: Optional[str],
        endpoint: str,
        method: str,
        body: Optional[str] = None,
        query_params: Optional[str] = None,
    ) -> Optional[ThreatEvent]:
        """Inspect an incoming request.

        Body content is ignored for natural-language endpoints (chat/voice/
        knowledge); query parameters are always inspected because they carry
        structured resource identifiers.
        """
        if endpoint.startswith(NATURAL_LANGUAGE_PREFIXES):
            body = None

        combined = f"{body or ''} {query_params or ''}".strip()

        if combined:
            # 1) OS command injection (CWE-78) — highest severity
            m = _COMMAND_INJECTION.search(combined)
            if m:
                return self._threat(
                    threat_type="command_injection",
                    severity="critical",
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    method=method,
                    description_ar="محاولة حقن أوامر نظام التشغيل",
                    description_en="Operating system command injection attempt",
                    evidence={"matched_pattern": m.group(0), "endpoint": endpoint},
                    blocked=True,
                )

            # 2) SQL injection (CWE-89)
            m = _SQL_INJECTION.search(combined)
            if m:
                return self._threat(
                    threat_type="sql_injection",
                    severity="high",
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    method=method,
                    description_ar="محاولة حقن SQL في طلب وارد",
                    description_en="SQL injection attempt detected",
                    evidence={"matched_pattern": m.group(0), "endpoint": endpoint},
                    blocked=True,
                )

            # 3) Path traversal (CWE-22)
            m = _PATH_TRAVERSAL.search(combined)
            if m:
                return self._threat(
                    threat_type="path_traversal",
                    severity="high",
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    method=method,
                    description_ar="محاولة اختراق المسار (Path Traversal)",
                    description_en="Path traversal attempt detected",
                    evidence={"matched_pattern": m.group(0), "endpoint": endpoint},
                    blocked=True,
                )

            # 4) XSS (CWE-79)
            m = _XSS_PATTERN.search(combined)
            if m:
                return self._threat(
                    threat_type="xss_attempt",
                    severity="medium",
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    method=method,
                    description_ar="محاولة حقن سكريبت خبيث (XSS)",
                    description_en="Cross-site scripting (XSS) attempt",
                    evidence={"matched_pattern": m.group(0), "endpoint": endpoint},
                    blocked=True,
                )

            # 5) Sensitive file access
            m = _SENSITIVE_PATH.search(combined)
            if m:
                return self._threat(
                    threat_type="sensitive_path_access",
                    severity="high",
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    method=method,
                    description_ar="محاولة الوصول إلى ملف حساس أو متغير بيئي",
                    description_en="Sensitive file or environment variable access attempt",
                    evidence={"matched_pattern": m.group(0), "endpoint": endpoint},
                    blocked=True,
                )

        # 6) Rate limiting (per IP and per user)
        if ip_address:
            dq = self._ip_requests[ip_address]
            dq.append(self._now())
            self._prune(dq, self.rate_limit_window)
            if len(dq) > self.rate_limit_max:
                return self._threat(
                    threat_type="rate_limit_abuse",
                    severity="medium",
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    method=method,
                    description_ar="إفراط في الطلبات من نفس العنوان IP",
                    description_en="Rate limit abuse from IP address",
                    evidence={
                        "requests_in_window": len(dq),
                        "window_seconds": self.rate_limit_window,
                        "max_allowed": self.rate_limit_max,
                    },
                    blocked=True,
                )

        if user_id:
            dq = self._user_requests[user_id]
            dq.append(self._now())
            self._prune(dq, self.rate_limit_window)
            if len(dq) > self.rate_limit_max:
                return self._threat(
                    threat_type="rate_limit_abuse",
                    severity="medium",
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    method=method,
                    description_ar="إفراط في الطلبات من نفس المستخدم",
                    description_en="Rate limit abuse from user account",
                    evidence={
                        "requests_in_window": len(dq),
                        "window_seconds": self.rate_limit_window,
                        "max_allowed": self.rate_limit_max,
                    },
                    blocked=True,
                )

        return None

    # ------------------------------------------------------------------
    # Event-specific detectors
    # ------------------------------------------------------------------

    def record_failure(
        self,
        *,
        user_id: Optional[str],
        ip_address: Optional[str],
        endpoint: str,
        method: str,
        failure_type: str = "auth",
    ) -> Optional[ThreatEvent]:
        """Record a failed authentication event and detect brute force."""
        now = self._now()
        if ip_address:
            dq = self._ip_failures[ip_address]
            dq.append(now)
            self._prune(dq, self.failure_window)
            if len(dq) >= self.failure_max:
                return self._threat(
                    threat_type="brute_force_auth",
                    severity="high",
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    method=method,
                    description_ar="محاولة اختراق بالقوة الغاشمة من نفس العنوان IP",
                    description_en="Brute force authentication attempt from IP address",
                    evidence={
                        "failures_in_window": len(dq),
                        "window_seconds": self.failure_window,
                        "max_allowed": self.failure_max,
                        "failure_type": failure_type,
                    },
                    blocked=True,
                )

        if user_id:
            dq = self._user_failures[user_id]
            dq.append(now)
            self._prune(dq, self.failure_window)
            if len(dq) >= self.failure_max:
                return self._threat(
                    threat_type="brute_force_auth",
                    severity="high",
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    method=method,
                    description_ar="محاولة اختراق بالقوة الغاشمة على حساب المستخدم",
                    description_en="Brute force authentication attempt against user account",
                    evidence={
                        "failures_in_window": len(dq),
                        "window_seconds": self.failure_window,
                        "max_allowed": self.failure_max,
                        "failure_type": failure_type,
                    },
                    blocked=True,
                )

        return None

    def record_totp_failure(
        self,
        *,
        user_id: str,
        ip_address: Optional[str],
        endpoint: str,
        method: str,
    ) -> Optional[ThreatEvent]:
        """Record a failed TOTP verification (RFC 6238 second factor)."""
        now = self._now()
        dq = self._totp_failures[user_id]
        dq.append(now)
        self._prune(dq, self.failure_window)
        if len(dq) >= self.totp_failure_max:
            return self._threat(
                threat_type="totp_brute_force",
                severity="critical",
                user_id=user_id,
                ip_address=ip_address,
                endpoint=endpoint,
                method=method,
                description_ar="محاولة اختراق رمز التحقق الثنائي (TOTP)",
                description_en="TOTP brute force attempt detected",
                evidence={
                    "failures_in_window": len(dq),
                    "window_seconds": self.failure_window,
                    "max_allowed": self.totp_failure_max,
                },
                blocked=True,
            )
        return None

    def detect_idor(
        self,
        *,
        user_id: str,
        resource_owner_id: str,
        resource_type: str,
        resource_id: str,
        ip_address: Optional[str],
        endpoint: str,
        method: str,
    ) -> Optional[ThreatEvent]:
        """Detect Insecure Direct Object Reference (CWE-639)."""
        if str(user_id) != str(resource_owner_id):
            return self._threat(
                threat_type="idor_attempt",
                severity="high",
                user_id=user_id,
                ip_address=ip_address,
                endpoint=endpoint,
                method=method,
                description_ar="محاولة الوصول إلى مورد يعود لمستخدم آخر (IDOR)",
                description_en="Insecure Direct Object Reference (IDOR) attempt",
                evidence={
                    "requesting_user": user_id,
                    "resource_owner": resource_owner_id,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                },
                blocked=True,
            )
        return None

    def detect_audit_tampering(
        self,
        *,
        user_id: str,
        ip_address: Optional[str],
        endpoint: str,
        method: str,
        operation: str,
    ) -> Optional[ThreatEvent]:
        """Detect attempts to modify or delete audit logs."""
        return self._threat(
            threat_type="audit_tampering",
            severity="critical",
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            method=method,
            description_ar="محاولة التعديل على سجلات التدقيق (Audit Tampering)",
            description_en="Audit log tampering attempt (append-only violation)",
            evidence={"attempted_operation": operation, "table": "audit_logs"},
            blocked=True,
        )

    def detect_privilege_escalation(
        self,
        *,
        user_id: str,
        user_role: str,
        required_role: str,
        ip_address: Optional[str],
        endpoint: str,
        method: str,
    ) -> Optional[ThreatEvent]:
        """Detect privilege escalation attempts (CWE-269)."""
        role_hierarchy = {"viewer": 0, "user": 1, "developer": 2, "admin": 3}
        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 99):
            return self._threat(
                threat_type="privilege_escalation",
                severity="high",
                user_id=user_id,
                ip_address=ip_address,
                endpoint=endpoint,
                method=method,
                description_ar="محاولة ترقية صلاحيات (Privilege Escalation)",
                description_en="Privilege escalation attempt detected",
                evidence={
                    "user_role": user_role,
                    "required_role": required_role,
                    "endpoint": endpoint,
                },
                blocked=True,
            )
        return None


# ---------------------------------------------------------------------------
# Bounded in-memory store (per worker)
# ---------------------------------------------------------------------------
#
# The store is intentionally process-local: it is a fast operational signal for
# the admin endpoint and structured logs. Durable, tamper-evident retention is
# the job of the append-only audit_logs table (see db/migrations/002).

_MAX_RECENT_THREATS = 1000
_recent_threats: deque[ThreatEvent] = deque(maxlen=_MAX_RECENT_THREATS)


def record_threat(event: Optional[ThreatEvent]) -> Optional[ThreatEvent]:
    """Append a detected threat to the bounded store. Returns the event."""
    if event is not None:
        _recent_threats.append(event)
    return event


def recent_threats(limit: int = 50) -> List[ThreatEvent]:
    """Return the most recent threats, oldest first."""
    if limit <= 0:
        return []
    return list(_recent_threats)[-limit:]


def threat_count() -> int:
    """Number of threats currently held in the store."""
    return len(_recent_threats)


def clear_threats() -> int:
    """Clear the store. Returns the number of removed events."""
    removed = len(_recent_threats)
    _recent_threats.clear()
    return removed


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------

threat_detector = ThreatDetector()
