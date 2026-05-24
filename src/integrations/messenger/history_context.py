"""
Messenger history context assembler.
Builds a rolling history window and composes a single contextual prompt string.
"""
from typing import Dict, List


def select_history_window(messages: List[Dict], max_turns: int, max_chars: int) -> List[Dict]:
    """
    Select the newest history within limits and return oldest -> newest ordering.
    """
    if max_turns <= 0:
        return []

    selected: List[Dict] = []
    total_chars = 0

    for message in reversed(messages):
        content = (message.get("content") or "").strip()
        if not content:
            continue

        line = _format_line(message.get("role", "user"), content)
        line_chars = len(line) + 1

        if selected and (len(selected) >= max_turns or total_chars + line_chars > max_chars):
            break

        selected.append(message)
        total_chars += line_chars

    return list(reversed(selected))


def build_contextual_user_input(history_messages: List[Dict], latest_user_message: str) -> str:
    """
    Compose one message string that includes prior turns and the current user message.
    """
    latest = latest_user_message.strip()
    filtered_messages = list(history_messages)
    if filtered_messages:
        tail = filtered_messages[-1]
        tail_content = (tail.get("content") or "").strip()
        if tail.get("role") == "user" and tail_content == latest:
            filtered_messages = filtered_messages[:-1]

    history_lines = []
    for msg in filtered_messages:
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        history_lines.append(_format_line(msg.get("role", "user"), content))

    history_block = "\n".join(history_lines) if history_lines else "(no previous messages)"

    return (
        "Use the previous conversation as context. Reply naturally and only to the current user message.\n\n"
        f"Previous conversation:\n{history_block}\n\n"
        f"Current user message:\n{latest}"
    )


def _format_line(role: str, content: str) -> str:
    label = "Assistant" if role == "assistant" else "User"
    return f"{label}: {content}"
