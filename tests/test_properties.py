import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from emotiv_recorder.properties import properties
from mo.core.plugin.models.properties import PropertyType


class TestProperties(unittest.TestCase):

    def test_client_id_exists(self):
        self.assertTrue(properties.has_property('client_id'))

    def test_client_secret_exists(self):
        self.assertTrue(properties.has_property('client_secret'))

    def test_client_id_is_text(self):
        self.assertEqual(properties.get_type('client_id'), PropertyType.TEXT)

    def test_client_secret_is_text(self):
        self.assertEqual(properties.get_type('client_secret'), PropertyType.TEXT)

    def test_client_id_default_empty(self):
        self.assertEqual(properties.get_default_values()['client_id'], '')

    def test_client_secret_default_empty(self):
        self.assertEqual(properties.get_default_values()['client_secret'], '')


if __name__ == '__main__':
    unittest.main()
