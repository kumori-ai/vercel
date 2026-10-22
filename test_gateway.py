"""Tests for gateway.py. No network, no key: the gateway's answers are faked.

    python3 -m unittest test_gateway
"""
import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import gateway

CATALOG = {'data': [
    {'id': 'a/free-chat', 'type': 'language', 'pricing': {'input': '0', 'output': '0'}, 'tags': ['free']},
    {'id': 'b/paid-chat', 'type': 'language', 'pricing': {'input': '0.000001', 'output': '0.000002'}},
    {'id': 'c/free-in-only', 'type': 'language', 'pricing': {'input': '0', 'output': '0.000002'}},
    {'id': 'f/free-out-only', 'type': 'language', 'pricing': {'input': '0.000001', 'output': '0'}},
    {'id': 'd/no-pricing', 'type': 'language'},
    {'id': 'e/free-image', 'type': 'image', 'pricing': {'input': '0', 'output': '0'}},
]}


class Free(unittest.TestCase):
    def test_only_models_priced_zero_in_and_out_count(self):
        with patch.object(gateway, '_req', return_value=(200, CATALOG)):
            total, free = gateway.free_models()
        self.assertEqual(total, 6)
        self.assertEqual([m['id'] for m in free], ['a/free-chat', 'e/free-image'])

    def test_a_catalog_error_stops_with_its_status(self):
        with patch.object(gateway, '_req', return_value=(500, {'error': 'down'})):
            with self.assertRaises(SystemExit) as e:
                gateway.free_models()
        self.assertIn('500', str(e.exception.code))


class Ping(unittest.TestCase):
    def test_ping_calls_only_free_language_models_with_eight_tokens(self):
        calls = []

        def fake(path, body=None, key=None, timeout=90):
            calls.append((path, body))
            if path == '/models':
                return 200, CATALOG
            if path == '/credits':
                return 200, {'balance': '5', 'total_used': '0'}
            return 200, {'usage': {'prompt_tokens': 9, 'completion_tokens': 1, 'cost': 0},
                         'choices': [{'message': {'content': 'pong'}}]}

        with patch.dict(os.environ, {'AI_GATEWAY_API_KEY': 'test'}), patch.object(gateway, '_req', side_effect=fake), \
                redirect_stdout(io.StringIO()) as out:
            gateway.cmd_ping()
        chats = [b for p, b in calls if p == '/chat/completions']
        self.assertEqual([b['model'] for b in chats], ['a/free-chat'])          # never a paid or image model
        self.assertTrue(all(b['max_tokens'] == 8 for b in chats))
        self.assertIn('cost=0', out.getvalue())

    def test_no_key_stops_before_any_call(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(gateway, '_req') as req:
            with self.assertRaises(SystemExit):
                gateway.cmd_ping()
        req.assert_not_called()


if __name__ == '__main__':
    unittest.main()
