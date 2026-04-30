import sys
import os
import json
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'emotiv_recorder'))

sys.modules['websocket'] = MagicMock()

from emotiv_data import EmotivData, EmotivMetrics, EmotivPower
import cortex_client as cortex_client_mod
CortexClient = cortex_client_mod.CortexClient


def make():
    return CortexClient("test_id", "test_secret")


class TestCortexClientInit(unittest.TestCase):

    def test_client_id_stored(self):
        c = CortexClient("my_id", "my_secret")
        self.assertEqual(c.client_id, "my_id")

    def test_client_secret_stored(self):
        c = CortexClient("my_id", "my_secret")
        self.assertEqual(c.client_secret, "my_secret")

    def test_ws_url(self):
        self.assertEqual(make().ws_url, "wss://localhost:6868")

    def test_init_flags(self):
        c = make()
        self.assertFalse(c.is_connected)
        self.assertFalse(c.should_run)

    def test_init_none_fields(self):
        c = make()
        self.assertIsNone(c.ws)
        self.assertIsNone(c.auth_token)
        self.assertIsNone(c.session_id)
        self.assertIsNone(c.headset_id)
        self.assertIsNone(c.thread)

    def test_init_request_id(self):
        self.assertEqual(make().request_id, 1)

    def test_listeners_empty(self):
        self.assertEqual(make().listeners, [])

    def test_latest_data_emotiv_data(self):
        self.assertIsInstance(make().latest_data, EmotivData)


class TestAddListener(unittest.TestCase):

    def test_adds_listener(self):
        c = make()
        fn = MagicMock()
        c.add_listener(fn)
        self.assertIn(fn, c.listeners)

    def test_no_duplicate(self):
        c = make()
        fn = MagicMock()
        c.add_listener(fn)
        c.add_listener(fn)
        self.assertEqual(len(c.listeners), 1)

    def test_multiple_listeners(self):
        c = make()
        fn1, fn2 = MagicMock(), MagicMock()
        c.add_listener(fn1)
        c.add_listener(fn2)
        self.assertEqual(len(c.listeners), 2)


class TestConnect(unittest.TestCase):

    def test_sets_run(self):
        c = make()
        with patch.object(cortex_client_mod.threading, 'Thread', return_value=MagicMock()):
            c.connect()
        self.assertTrue(c.should_run)

    def test_starts_thread(self):
        c = make()
        mock_t = MagicMock()
        with patch.object(cortex_client_mod.threading, 'Thread', return_value=mock_t):
            c.connect()
        mock_t.start.assert_called_once()

    def test_thread_stored(self):
        c = make()
        mock_t = MagicMock()
        with patch.object(cortex_client_mod.threading, 'Thread', return_value=mock_t):
            c.connect()
        self.assertIs(c.thread, mock_t)


class TestDisconnect(unittest.TestCase):

    def test_clears_run(self):
        c = make()
        c.should_run = True
        c.ws = MagicMock()
        c.thread = MagicMock(is_alive=lambda: False)
        c.disconnect()
        self.assertFalse(c.should_run)

    def test_closes_ws(self):
        c = make()
        mock_ws = MagicMock()
        c.ws = mock_ws
        c.thread = MagicMock(is_alive=lambda: False)
        c.disconnect()
        mock_ws.close.assert_called_once()

    def test_sets_not_connected(self):
        c = make()
        c.is_connected = True
        c.ws = MagicMock()
        c.thread = MagicMock(is_alive=lambda: False)
        c.disconnect()
        self.assertFalse(c.is_connected)

    def test_no_ws_ok(self):
        c = make()
        c.ws = None
        c.thread = None
        c.disconnect()

    def test_joins_alive_thread(self):
        c = make()
        c.ws = MagicMock()
        mock_t = MagicMock()
        mock_t.is_alive.return_value = True
        c.thread = mock_t
        c.disconnect()
        mock_t.join.assert_called_once_with(timeout=1.0)

    def test_not_join_dead_thread(self):
        c = make()
        c.ws = MagicMock()
        mock_t = MagicMock()
        mock_t.is_alive.return_value = False
        c.thread = mock_t
        c.disconnect()
        mock_t.join.assert_not_called()


class TestSendJson(unittest.TestCase):

    def connected_client(self):
        c = make()
        mock_ws = MagicMock()
        mock_ws.sock = MagicMock()
        mock_ws.sock.connected = True
        c.ws = mock_ws
        return c, mock_ws

    def test_sends_payload_connected(self):
        c, mock_ws = self.connected_client()
        c.send_json("myMethod", {"key": "val"})
        mock_ws.send.assert_called_once()
        payload = json.loads(mock_ws.send.call_args[0][0])
        self.assertEqual(payload["method"], "myMethod")
        self.assertEqual(payload["params"], {"key": "val"})
        self.assertEqual(payload["jsonrpc"], "2.0")

    def test_request_id_payload(self):
        c, mock_ws = self.connected_client()
        c.send_json("m", {})
        payload = json.loads(mock_ws.send.call_args[0][0])
        self.assertEqual(payload["id"], 1)

    def test_increments_request_id(self):
        c, mock_ws = self.connected_client()
        c.send_json("m1", {})
        c.send_json("m2", {})
        self.assertEqual(c.request_id, 3)

    def test_no_send_ws_none(self):
        c = make()
        c.ws = None
        c.send_json("m", {})

    def test_no_send_sock_none(self):
        c = make()
        mock_ws = MagicMock()
        mock_ws.sock = None
        c.ws = mock_ws
        c.send_json("m", {})
        mock_ws.send.assert_not_called()

    def test_no_send_not_connected(self):
        c = make()
        mock_ws = MagicMock()
        mock_ws.sock = MagicMock()
        mock_ws.sock.connected = False
        c.ws = mock_ws
        c.send_json("m", {})
        mock_ws.send.assert_not_called()

    def test_send_exception_silenced(self):
        c, mock_ws = self.connected_client()
        mock_ws.send.side_effect = Exception("network error")
        c.send_json("m", {})


class TestOnOpen(unittest.TestCase):

    def test_sets_is_connected(self):
        c = make()
        c.send_json = MagicMock()
        c.on_open(MagicMock())
        self.assertTrue(c.is_connected)

    def test_sends_request_access(self):
        c = make()
        c.send_json = MagicMock()
        c.on_open(MagicMock())
        c.send_json.assert_called_once_with("requestAccess", {
            "clientId": "test_id",
            "clientSecret": "test_secret"
        })


class TestOnMessage(unittest.TestCase):

    def setUp(self):
        self.c = make()
        self.c.send_json = MagicMock()

    def test_invalid_json_ignored(self):
        self.c.on_message(MagicMock(), "not-valid-json")
        self.c.send_json.assert_not_called()

    def test_access_sends_authorize(self):
        msg = json.dumps({"result": {"accessGranted": True}})
        self.c.on_message(MagicMock(), msg)
        self.c.send_json.assert_called_with("authorize", {
            "clientId": "test_id", "clientSecret": "test_secret"
        })

    def test_cortex_token_saves_token(self):
        msg = json.dumps({"result": {"cortexToken": "tok123"}})
        self.c.on_message(MagicMock(), msg)
        self.assertEqual(self.c.auth_token, "tok123")

    def test_cortex_token_queries_headsets(self):
        msg = json.dumps({"result": {"cortexToken": "tok123"}})
        self.c.on_message(MagicMock(), msg)
        self.c.send_json.assert_called_with("queryHeadsets", {})

    def test_headset_list_connected_saves_headset_id(self):
        self.c.auth_token = "tok"
        msg = json.dumps({"result": [{"id": "H1", "status": "connected"}]})
        self.c.on_message(MagicMock(), msg)
        self.assertEqual(self.c.headset_id, "H1")

    def test_headset_list_connected_creates_session(self):
        self.c.auth_token = "tok"
        msg = json.dumps({"result": [{"id": "H1", "status": "connected"}]})
        self.c.on_message(MagicMock(), msg)
        self.c.send_json.assert_called_with("createSession", {
            "cortexToken": "tok", "headset": "H1", "status": "active"
        })

    def test_headset_list_first_connected_wins(self):
        self.c.auth_token = "tok"
        msg = json.dumps({"result": [
            {"id": "H1", "status": "connected"},
            {"id": "H2", "status": "connected"}
        ]})
        self.c.on_message(MagicMock(), msg)
        self.assertEqual(self.c.headset_id, "H1")

    def test_headset_list_none_connected_retries(self):
        with patch.object(cortex_client_mod.time, 'sleep'):
            msg = json.dumps({"result": [{"id": "H1", "status": "disconnected"}]})
            self.c.on_message(MagicMock(), msg)
        self.c.send_json.assert_called_with("queryHeadsets", {})

    def test_headset_list_empty_retries(self):
        with patch.object(cortex_client_mod.time, 'sleep'):
            msg = json.dumps({"result": []})
            self.c.on_message(MagicMock(), msg)
        self.c.send_json.assert_called_with("queryHeadsets", {})

    def test_session_created_saves_session_id(self):
        self.c.auth_token = "tok"
        msg = json.dumps({"result": {"id": "sess1", "appId": "app1"}})
        self.c.on_message(MagicMock(), msg)
        self.assertEqual(self.c.session_id, "sess1")

    def test_session_created_subscribes_streams(self):
        self.c.auth_token = "tok"
        msg = json.dumps({"result": {"id": "sess1", "appId": "app1"}})
        self.c.on_message(MagicMock(), msg)
        self.c.send_json.assert_called_with("subscribe", {
            "cortexToken": "tok", "session": "sess1",
            "streams": ["met", "pow", "sys"]
        })

    def test_sid_in_data_calls_process_stream(self):
        self.c.process_stream_data = MagicMock()
        msg = json.dumps({"sid": "s1", "time": 1.0, "met": [0.1] * 6})
        self.c.on_message(MagicMock(), msg)
        self.c.process_stream_data.assert_called_once()

    def test_no_result_no_send(self):
        msg = json.dumps({"other": "data"})
        self.c.on_message(MagicMock(), msg)
        self.c.send_json.assert_not_called()


class TestProcessStreamData(unittest.TestCase):

    def setUp(self):
        self.c = make()
        self.listener = MagicMock()
        self.c.add_listener(self.listener)

    def test_met_data_updates_metrics(self):
        data = {"time": 1.0, "met": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]}
        self.c.process_stream_data(data)
        pkt = self.listener.call_args[0][0]
        self.assertAlmostEqual(pkt.metrics.engagement, 0.1)
        self.assertAlmostEqual(pkt.metrics.excitement, 0.2)
        self.assertAlmostEqual(pkt.metrics.stress, 0.3)
        self.assertAlmostEqual(pkt.metrics.relaxation, 0.4)
        self.assertAlmostEqual(pkt.metrics.interest, 0.5)
        self.assertAlmostEqual(pkt.metrics.focus, 0.6)

    def test_pow_data_updates_power(self):
        data = {"time": 1.0, "pow": [5.0, 8.0, 13.0, 20.0, 30.0]}
        self.c.process_stream_data(data)
        pkt = self.listener.call_args[0][0]
        self.assertAlmostEqual(pkt.power.theta, 5.0)
        self.assertAlmostEqual(pkt.power.alpha, 8.0)
        self.assertAlmostEqual(pkt.power.low_beta, 13.0)
        self.assertAlmostEqual(pkt.power.high_beta, 20.0)
        self.assertAlmostEqual(pkt.power.gamma, 30.0)

    def test_met_no_emit(self):
        self.c.process_stream_data({"time": 1.0, "met": [0.1, 0.2]})
        self.listener.assert_not_called()

    def test_pow_too_short_no_emit(self):
        self.c.process_stream_data({"time": 1.0, "pow": [1.0, 2.0]})
        self.listener.assert_not_called()

    def test_no_met_no_pow_no_emit(self):
        self.c.process_stream_data({"time": 1.0})
        self.listener.assert_not_called()

    def test_none_values_in_met_default_to_zero(self):
        data = {"time": 1.0, "met": [None] * 6}
        self.c.process_stream_data(data)
        pkt = self.listener.call_args[0][0]
        self.assertAlmostEqual(pkt.metrics.engagement, 0.0)
        self.assertAlmostEqual(pkt.metrics.focus, 0.0)

    def test_none_values_in_pow_default_to_zero(self):
        data = {"time": 1.0, "pow": [None] * 5}
        self.c.process_stream_data(data)
        pkt = self.listener.call_args[0][0]
        self.assertAlmostEqual(pkt.power.theta, 0.0)
        self.assertAlmostEqual(pkt.power.gamma, 0.0)

    def test_timestamp_set_from_data(self):
        data = {"time": 42.5, "met": [0.1] * 6}
        self.c.process_stream_data(data)
        pkt = self.listener.call_args[0][0]
        self.assertAlmostEqual(pkt.timestamp, 42.5)

    def test_packet_is_copy_not_same_object(self):
        data = {"time": 1.0, "met": [0.5] * 6}
        self.c.process_stream_data(data)
        pkt = self.listener.call_args[0][0]
        self.assertIsNot(pkt, self.c.latest_data)

    def test_multiple_listeners_all_called(self):
        fn2 = MagicMock()
        self.c.add_listener(fn2)
        self.c.process_stream_data({"time": 1.0, "met": [0.1] * 6})
        self.listener.assert_called_once()
        fn2.assert_called_once()

    def test_met_and_pow_together_emits_once(self):
        data = {"time": 1.0, "met": [0.1] * 6, "pow": [1.0] * 5}
        self.c.process_stream_data(data)
        self.listener.assert_called_once()

    def test_power_all_fields_copied_to_packet(self):
        data = {"time": 1.0, "pow": [5.0, 8.0, 13.0, 20.0, 30.0]}
        self.c.process_stream_data(data)
        pkt = self.listener.call_args[0][0]
        self.assertAlmostEqual(pkt.power.alpha, 8.0)
        self.assertAlmostEqual(pkt.power.low_beta, 13.0)
        self.assertAlmostEqual(pkt.power.high_beta, 20.0)


class TestOnErrorAndClose(unittest.TestCase):

    def test_on_error_no_exception(self):
        make().on_error(MagicMock(), Exception("some error"))

    def test_on_close_no_exception(self):
        make().on_close(MagicMock(), 1000, "closed normally")

    def test_on_close_with_none_args(self):
        make().on_close(MagicMock(), None, None)


if __name__ == '__main__':
    unittest.main()
