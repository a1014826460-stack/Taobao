import unittest
from unittest import mock

from src.tests import taobao_test


class TaobaoRequestTest(unittest.TestCase):
    def test_build_session_ignores_system_proxy_by_default(self):
        session = taobao_test.build_session()
        self.assertFalse(session.trust_env)

    def test_configure_stdout_utf8_reconfigures_stdout_when_supported(self):
        fake_stdout = mock.Mock()
        with mock.patch.object(taobao_test.sys, 'stdout', fake_stdout):
            taobao_test.configure_stdout_utf8()
        fake_stdout.reconfigure.assert_called_once_with(encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
