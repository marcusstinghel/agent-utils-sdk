"""Unit tests for the messaging module."""

import json
from types import SimpleNamespace

import pytest

from agent_utils_sdk.messaging import Envelope, MessageHandler, SubjectBuilder


def test_envelope_keeps_extra_fields():
    env = Envelope(user_id="u1", message_id="m1", order_ref="o-9")
    assert env.model_dump()["order_ref"] == "o-9"
    assert env.metadata == {}


def test_subject_builder_with_mapping_and_missing_value():
    builder = SubjectBuilder(prefix="app", fields=("user_id", "event_type"))
    assert builder.build({"user_id": "u1"}) == "app.u1._"


def test_subject_builder_custom_separator():
    builder = SubjectBuilder(fields=("user_id", "event_type"), separator="/")
    assert builder.build({"user_id": "u1", "event_type": "greet"}) == "u1/greet"


def test_subject_builder_rejects_whitespace_in_prefix():
    with pytest.raises(ValueError):
        SubjectBuilder(prefix="a b").build({"user_id": "u", "message_id": "m"})


def test_pattern_with_fixed_value_and_invalid_value():
    builder = SubjectBuilder(fields=("user_id", "event_type"))
    assert builder.pattern(user_id="u1") == "u1.*"
    with pytest.raises(ValueError):
        builder.pattern(user_id="a.b")


def test_parse_accepts_message_like_objects():
    payload = {"user_id": "u1", "message_id": "m1"}
    msg = SimpleNamespace(data=json.dumps([payload]).encode())
    assert MessageHandler().parse(msg).user_id == "u1"


def test_parse_rejects_non_object_payloads():
    handler = MessageHandler()
    with pytest.raises(ValueError, match="JSON object"):
        handler.parse(b"[1]")
    with pytest.raises(ValueError, match="exactly one"):
        handler.parse(b"[]")
    with pytest.raises(ValueError, match="not valid JSON"):
        handler.parse(None)


def test_parse_reports_invalid_fields():
    with pytest.raises(ValueError, match="message_id"):
        MessageHandler().parse({"user_id": "u1"})


def test_to_subject_and_require_role():
    handler = MessageHandler(subject_builder=SubjectBuilder(prefix="svc", fields=("user_id",)))
    assert handler.to_subject({"user_id": "u1"}) == "svc.u1"
    assert handler.require_role("admin", {"admin"}) is True
    with pytest.raises(PermissionError):
        handler.require_role(None, ["admin"])
