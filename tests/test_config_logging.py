import io
import logging
import unittest

from core.config import EngineConfig
from core.logging import configure_logger


class ConfigLoggingTest(unittest.TestCase):
    def test_config_hash_is_stable(self):
        first = EngineConfig(symbol="BTCUSDT").hash()
        second = EngineConfig(symbol="BTCUSDT").hash()

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_configure_logger_is_idempotent(self):
        stream = io.StringIO()
        logger = configure_logger("tm_trading_v555_test", level=logging.INFO, stream=stream)
        same_logger = configure_logger("tm_trading_v555_test", level=logging.INFO, stream=stream)

        logger.info("logger works")

        self.assertIs(logger, same_logger)
        self.assertEqual(len(logger.handlers), 1)
        self.assertIn("logger works", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
