import unittest

from matterbot_contracts import is_valid_legacy_response, validate_legacy_response


class LegacyResponseContractTests(unittest.TestCase):
    def test_none_is_valid_noop_response(self):
        self.assertEqual([], validate_legacy_response(None))
        self.assertTrue(is_valid_legacy_response(None))

    def test_minimal_legacy_message_is_valid(self):
        result = {"messages": [{"text": "ok"}]}
        self.assertEqual([], validate_legacy_response(result))

    def test_upload_message_is_valid(self):
        result = {
            "messages": [
                {
                    "text": "attached",
                    "uploads": [{"filename": "report.txt", "bytes": "hello"}],
                }
            ]
        }
        self.assertEqual([], validate_legacy_response(result))

    def test_result_must_be_dict_or_none(self):
        self.assertEqual(["response must be a dict or None"], validate_legacy_response("bad"))

    def test_messages_key_is_required(self):
        self.assertEqual(["response missing required 'messages' list"], validate_legacy_response({}))

    def test_messages_must_be_list(self):
        self.assertEqual(["response 'messages' must be a list"], validate_legacy_response({"messages": "bad"}))

    def test_message_must_be_dict(self):
        self.assertEqual(["messages[0] must be a dict"], validate_legacy_response({"messages": ["bad"]}))

    def test_text_must_be_string_when_present(self):
        self.assertEqual(
            ["messages[0].text must be a string"],
            validate_legacy_response({"messages": [{"text": 123}]}),
        )

    def test_message_needs_text_or_uploads(self):
        self.assertEqual(
            ["messages[0] must contain 'text' or 'uploads'"],
            validate_legacy_response({"messages": [{}]}),
        )

    def test_uploads_must_be_list_or_none(self):
        self.assertEqual(
            ["messages[0].uploads must be a list or None"],
            validate_legacy_response({"messages": [{"text": "x", "uploads": "bad"}]}),
        )

    def test_upload_must_have_filename_and_bytes(self):
        self.assertEqual(
            [
                "messages[0].uploads[0].filename must be a non-empty string",
                "messages[0].uploads[0] missing required 'bytes'",
            ],
            validate_legacy_response({"messages": [{"text": "x", "uploads": [{}]}]}),
        )

    def test_upload_bytes_must_be_bytes_or_string(self):
        self.assertEqual(
            ["messages[0].uploads[0].bytes must be bytes, bytearray, or string"],
            validate_legacy_response(
                {"messages": [{"text": "x", "uploads": [{"filename": "x", "bytes": object()}]}]}
            ),
        )

    def test_is_valid_legacy_response_returns_false_for_errors(self):
        self.assertFalse(is_valid_legacy_response({"messages": [{}]}))


if __name__ == "__main__":
    unittest.main()
