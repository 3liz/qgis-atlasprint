"""Test core functions."""

from qgis.testing import unittest

def test_global_scales(client):

        from atlasprintServer.core import global_scales

        """Test we can fetch global scales from INI file or hardcoded scales."""
        scales = global_scales()
        expected = [
            1000000, 500000, 250000, 100000, 50000, 25000, 10000, 5000, 2500, 1000, 500
        ]
        assert scales == expected

def test_not_supported_request(client):
    """  Test getcapabilites response
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=ATLAS&REQUEST=Get&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400

