"""Test core functions."""

from qgis.testing import unittest

from ..filters.core import global_scales

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestAtlas(unittest.TestCase):

    def test_global_scales(self):
        """Test we can fetch global scales from INI file or hardcoded scales."""
        scales = global_scales()
        expected = [
            1000000, 500000, 250000, 100000, 50000, 25000, 10000, 5000, 2500, 1000, 500
        ]
        self.assertListEqual(scales, expected)
