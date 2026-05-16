"""Contract helpers for MatterBot module responses.

These helpers are intentionally dependency-free so they can be used by tests,
future diagnostics, and eventually PR27 structured-output migration work without
pulling in Mattermost or any command module dependencies.
"""


def validate_legacy_response(result):
    """Return a list of contract errors for the legacy module response shape.

    Valid legacy command modules return either ``None`` for no output or a dict
    shaped like ``{'messages': [{'text': '...'}]}``. Messages may optionally
    include an ``uploads`` list, where each upload contains ``filename`` and
    ``bytes`` keys. This validator reports all obvious shape errors instead of
    raising so callers can show useful diagnostics.
    """
    if result is None:
        return []

    if not isinstance(result, dict):
        return ["response must be a dict or None"]

    if "messages" not in result or not isinstance(result.get("messages"), list):
        if "messages" not in result:
            return ["response missing required 'messages' list"]
        return ["response 'messages' must be a list"]

    errors = []
    for message_index, message in enumerate(result["messages"]):
        prefix = f"messages[{message_index}]"
        if not isinstance(message, dict):
            errors.append(f"{prefix} must be a dict")
            continue

        if "text" not in message and "uploads" not in message:
            errors.append(f"{prefix} must contain 'text' or 'uploads'")

        if "text" in message and not isinstance(message["text"], str):
            errors.append(f"{prefix}.text must be a string")

        if "uploads" in message:
            errors.extend(_validate_uploads(message["uploads"], f"{prefix}.uploads"))

    return errors


def is_valid_legacy_response(result):
    """Return True when ``result`` satisfies the legacy response contract."""
    return not validate_legacy_response(result)


def _validate_uploads(uploads, prefix):
    if uploads is None:
        return []

    if not isinstance(uploads, list):
        return [f"{prefix} must be a list or None"]

    errors = []
    for upload_index, upload in enumerate(uploads):
        upload_prefix = f"{prefix}[{upload_index}]"
        if not isinstance(upload, dict):
            errors.append(f"{upload_prefix} must be a dict")
            continue

        filename = upload.get("filename")
        if not isinstance(filename, str) or not filename:
            errors.append(f"{upload_prefix}.filename must be a non-empty string")

        if "bytes" not in upload:
            errors.append(f"{upload_prefix} missing required 'bytes'")
        elif not isinstance(upload["bytes"], (bytes, bytearray, str)):
            errors.append(f"{upload_prefix}.bytes must be bytes, bytearray, or string")

    return errors
