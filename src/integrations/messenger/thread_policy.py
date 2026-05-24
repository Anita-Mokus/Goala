"""
Messenger thread policy helpers.
"""


def is_likely_group_chat(display_name: str) -> bool:
    """
    Best-effort group chat detection from conversation display name.

    This heuristic intentionally errs on the safe side because group chats
    are disallowed for this bot.
    """
    name = (display_name or "").strip()
    if not name:
        return False

    lowered = name.lower()

    separators = [",", " & ", " + ", " és ", " and "]
    if any(token in lowered for token in separators):
        return True

    group_keywords = ["group", "csoport"]
    if any(keyword in lowered for keyword in group_keywords):
        return True

    return False
