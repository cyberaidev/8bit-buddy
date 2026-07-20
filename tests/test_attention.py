from __future__ import annotations

import unittest

from eightbit_buddy.attention import needs_user_attention


class AttentionTests(unittest.TestCase):
    def test_explicit_request_is_attention(self) -> None:
        self.assertTrue(needs_user_attention("I need your confirmation before deployment."))
        self.assertTrue(needs_user_attention("Which environment should I use?"))

    def test_polite_offer_is_not_automatically_attention(self) -> None:
        self.assertFalse(needs_user_attention("Done. Let me know if you want further changes."))
        self.assertFalse(needs_user_attention("All tests pass."))


if __name__ == "__main__":
    unittest.main()
