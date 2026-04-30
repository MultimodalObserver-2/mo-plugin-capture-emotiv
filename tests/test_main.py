import sys
import os
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mo.modules.capture import CaptureData


class MockSettings:
    def __init__(self, data=None):
        self._data = data or {}

    def get_setting(self, key):
        return self._data.get(key)


class MockMetrics:
    stress = 0.1
    engagement = 0.2
    interest = 0.3
    excitement = 0.4
    focus = 0.5
    relaxation = 0.6


class MockPower:
    theta = 0.01
    alpha = 0.02
    low_beta = 0.03
    high_beta = 0.04
    gamma = 0.05


class MockEmotivData:
    timestamp = 1000.0
    metrics = MockMetrics()
    power = MockPower()
    battery_level = 80
    headset_id = 'EPOCX-001'


class MockCortexClient:
    def __init__(self, *args):
        self._listener = None

    def add_listener(self, fn):
        self._listener = fn

    def connect(self):
        pass

    def disconnect(self):
        pass


mock_emotiv_data = MagicMock()
mock_emotiv_data.EmotivData = MockEmotivData

sys.modules['cortex_client'] = MagicMock(CortexClient=MockCortexClient)
sys.modules['emotiv_data'] = mock_emotiv_data

from emotiv_recorder.main import EmotivCapturePlugin

del sys.modules['emotiv_data']


def make():
    p = EmotivCapturePlugin()
    p.settings = MockSettings()
    return p


class StopLoop:
    def __init__(self, plugin):
        self.plugin = plugin

    def __call__(self, *_):
        self.plugin.is_capturing = False


class RecordAndStop:
    def __init__(self, plugin, states, attr):
        self.plugin = plugin
        self.states = states
        self.attr = attr

    def __call__(self, *_):
        self.states.append(getattr(self.plugin, self.attr))
        self.plugin.is_capturing = False


class TrackConnect:
    def __init__(self, connected):
        self.connected = connected

    def __call__(self, *_):
        self.connected[0] = True


class TestMain(unittest.TestCase):

    def run_start(self, p, on_data=None):
        if on_data is None:
            on_data = MagicMock()
        with patch('emotiv_recorder.main.time.sleep', side_effect=StopLoop(p)):
            p.start(0.0, MagicMock(), on_data)

    def test_load_resets_state(self):
        p = make()
        p.is_capturing = True
        p.is_paused = True
        p.load()
        self.assertFalse(p.is_capturing)
        self.assertFalse(p.is_paused)

    def test_load_initial_state(self):
        p = make()
        self.assertIsNone(p.client)
        self.assertIsNone(p.file_path)
        self.assertFalse(p.is_capturing)
        self.assertFalse(p.is_paused)

    def test_prepare_creates_json(self):
        p = make()
        with tempfile.TemporaryDirectory() as d:
            p.prepare(d, 'test')
            expected = Path(d) / 'test.json'
            self.assertTrue(expected.exists())
            with open(expected) as f:
                self.assertEqual(json.load(f), [])

    def test_prepare_sets_file_path(self):
        p = make()
        with tempfile.TemporaryDirectory() as d:
            p.prepare(d, 'rec')
            self.assertEqual(p.file_path, Path(d) / 'rec.json')

    def test_pause_sets_is_paused(self):
        p = make()
        p.is_capturing = True
        p.pause(10.0)
        self.assertTrue(p.is_paused)

    def test_pause_not_capturing(self):
        p = make()
        p.is_capturing = False
        p.pause(10.0)
        self.assertFalse(p.is_paused)

    def test_resume_clears_paused(self):
        p = make()
        p.is_capturing = True
        p.is_paused = True
        p.resume(20.0)
        self.assertFalse(p.is_paused)

    def test_resume_not_capturing(self):
        p = make()
        p.is_capturing = False
        p.is_paused = True
        p.resume(20.0)
        self.assertTrue(p.is_paused)

    def test_stop_sets_not_capturing(self):
        p = make()
        p.is_capturing = True
        mock_client = MagicMock()
        p.client = mock_client
        p.stop(100.0)
        self.assertFalse(p.is_capturing)

    def test_stop_client_cleared(self):
        p = make()
        p.is_capturing = True
        mock_client = MagicMock()
        p.client = mock_client
        p.stop(100.0)
        mock_client.disconnect.assert_called_once()
        self.assertIsNone(p.client)

    def test_stop_no_client(self):
        p = make()
        p.is_capturing = True
        p.client = None
        p.stop(100.0)

    def test_save_appends_to_json(self):
        p = make()
        with tempfile.TemporaryDirectory() as d:
            p.file_path = Path(d) / 'data.json'
            p.file_path.write_text('[]')
            data = {'timestamp': 1.0, 'val': 42}
            cd = CaptureData(timestamp=1.0, data=data)
            p.save([cd])
            result = json.loads(p.file_path.read_text())
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['val'], 42)

    def test_save_no_file_path(self):
        p = make()
        p.file_path = None
        p.save([CaptureData(timestamp=1.0, data={'x': 1})])

    def test_save_empty_data(self):
        p = make()
        with tempfile.TemporaryDirectory() as d:
            p.file_path = Path(d) / 'data.json'
            p.file_path.write_text('[]')
            p.save([])

    def test_save_corrupted_json_recovers(self):
        p = make()
        with tempfile.TemporaryDirectory() as d:
            p.file_path = Path(d) / 'data.json'
            p.file_path.write_text('INVALID')
            cd = CaptureData(timestamp=1.0, data={'val': 1})
            p.save([cd])
            result = json.loads(p.file_path.read_text())
            self.assertEqual(len(result), 1)

    def test_save_multiple_items(self):
        p = make()
        with tempfile.TemporaryDirectory() as d:
            p.file_path = Path(d) / 'data.json'
            p.file_path.write_text('[]')
            items = [CaptureData(timestamp=float(i), data={'v': i}) for i in range(5)]
            p.save(items)
            result = json.loads(p.file_path.read_text())
            self.assertEqual(len(result), 5)

    def test_on_emotiv_data_calls_callback(self):
        p = make()
        p.is_capturing = True
        p.is_paused = False
        mock_cb = MagicMock()
        p.on_data_callback = mock_cb
        data = MockEmotivData()
        p.on_emotiv_data(data)
        mock_cb.assert_called_once()
        cd = mock_cb.call_args[0][0]
        self.assertEqual(cd.timestamp, 1000.0)
        self.assertIn('metrics', cd.data)
        self.assertIn('power', cd.data)
        self.assertIn('status', cd.data)

    def test_on_emotiv_data_paused(self):
        p = make()
        p.is_capturing = True
        p.is_paused = True
        mock_cb = MagicMock()
        p.on_data_callback = mock_cb
        p.on_emotiv_data(MockEmotivData())
        mock_cb.assert_not_called()

    def test_on_emotiv_data_not_capturing(self):
        p = make()
        p.is_capturing = False
        p.is_paused = False
        mock_cb = MagicMock()
        p.on_data_callback = mock_cb
        p.on_emotiv_data(MockEmotivData())
        mock_cb.assert_not_called()

    def test_on_emotiv_data_no_callback(self):
        p = make()
        p.is_capturing = True
        p.is_paused = False
        p.on_data_callback = None
        p.on_emotiv_data(MockEmotivData())

    def test_on_emotiv_data_metrics_values(self):
        p = make()
        p.is_capturing = True
        p.is_paused = False
        mock_cb = MagicMock()
        p.on_data_callback = mock_cb
        p.on_emotiv_data(MockEmotivData())
        cd = mock_cb.call_args[0][0]
        self.assertAlmostEqual(cd.data['metrics']['stress'], 0.1)
        self.assertAlmostEqual(cd.data['metrics']['focus'], 0.5)

    def test_on_emotiv_data_power_values(self):
        p = make()
        p.is_capturing = True
        p.is_paused = False
        mock_cb = MagicMock()
        p.on_data_callback = mock_cb
        p.on_emotiv_data(MockEmotivData())
        cd = mock_cb.call_args[0][0]
        self.assertAlmostEqual(cd.data['power']['theta'], 0.01)
        self.assertAlmostEqual(cd.data['power']['gamma'], 0.05)

    def test_on_emotiv_data_status_values(self):
        p = make()
        p.is_capturing = True
        p.is_paused = False
        mock_cb = MagicMock()
        p.on_data_callback = mock_cb
        p.on_emotiv_data(MockEmotivData())
        cd = mock_cb.call_args[0][0]
        self.assertEqual(cd.data['status']['battery'], 80)
        self.assertEqual(cd.data['status']['headset'], 'EPOCX-001')

    def test_extension(self):
        self.assertEqual(make().get_file_extension(), 'json')

    def test_descriptor_structure(self):
        d = make().get_output_descriptor()
        self.assertIsNotNone(d)
        self.assertIn('type', d)
        self.assertIn('properties', d)
        self.assertIn('metrics', d['properties'])
        self.assertIn('power', d['properties'])

    def test_unload_calls_stop(self):
        p = make()
        p.is_capturing = True
        mock_client = MagicMock()
        p.client = mock_client
        p.unload()
        mock_client.disconnect.assert_called_once()

    def test_start_sets_on_data_callback(self):
        p = make()
        mock_cb = MagicMock()
        self.run_start(p, mock_cb)
        self.assertEqual(p.on_data_callback, mock_cb)

    def test_start_creates_client(self):
        p = make()
        self.run_start(p)
        self.assertIsNotNone(p.client)

    def test_start_is_capturing_in_loop(self):
        p = make()
        states = []
        with patch('emotiv_recorder.main.time.sleep', side_effect=RecordAndStop(p, states, 'is_capturing')):
            p.start(0.0, MagicMock(), MagicMock())
        self.assertTrue(states[0])

    def test_start_not_paused(self):
        p = make()
        p.is_paused = True
        states = []
        with patch('emotiv_recorder.main.time.sleep', side_effect=RecordAndStop(p, states, 'is_paused')):
            p.start(0.0, MagicMock(), MagicMock())
        self.assertFalse(states[0])

    def test_start_adds_listener(self):
        p = make()
        self.run_start(p)
        self.assertIsNotNone(p.client._listener)

    def test_start_client_called(self):
        p = make()
        connected = [False]
        with patch.object(MockCortexClient, 'connect', TrackConnect(connected)):
            self.run_start(p)
        self.assertTrue(connected[0])


if __name__ == '__main__':
    unittest.main()
