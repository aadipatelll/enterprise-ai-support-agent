import pytest

from app.prompts import PROMPT_VERSIONS, build_prompt, format_context
from tests.conftest import PTO_CHUNK, VPN_CHUNK


def test_format_context_numbers_sources_with_metadata() -> None:
    context = format_context([PTO_CHUNK, VPN_CHUNK])

    assert context.startswith("[1] Paid Time Off Policy > Carryover (hr-pto-policy.md)\n")
    assert "[2] VPN Access > Limits (it-vpn-access.md)" in context


@pytest.mark.parametrize("version", PROMPT_VERSIONS)
def test_every_prompt_version_renders(version: str) -> None:
    messages = build_prompt(version).format_messages(question="Q?", context="[1] ctx")

    assert "INSUFFICIENT_CONTEXT" in messages[0].content
    assert messages[1].content.endswith("Question: Q?")


def test_unknown_prompt_version_raises() -> None:
    with pytest.raises(ValueError, match="Unknown prompt version"):
        build_prompt("v99")
