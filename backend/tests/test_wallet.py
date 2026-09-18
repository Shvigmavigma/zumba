import unittest

from pydantic import ValidationError

from app.schemas import CoinAdjustment
from app.wallet import InsufficientCoinsError, next_coin_balance


class WalletTest(unittest.TestCase):
    def test_adjustment_is_positive_and_has_a_reason(self):
        adjustment = CoinAdjustment(coins=25, reason="  race prize  ")
        self.assertEqual(adjustment.coins, 25)
        self.assertEqual(adjustment.reason, "race prize")
        with self.assertRaises(ValidationError):
            CoinAdjustment(coins=0, reason="zero")
        with self.assertRaises(ValidationError):
            CoinAdjustment(coins=1, reason="   ")

    def test_balance_never_becomes_negative(self):
        self.assertEqual(next_coin_balance(10, -3), 7)
        with self.assertRaises(InsufficientCoinsError):
            next_coin_balance(2, -3)


if __name__ == "__main__":
    unittest.main()
