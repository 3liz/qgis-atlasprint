""" Test a not atlas function. """

import json

from .core.client import Client

PROJECT_FILE = 'no_atlas.qgs'


def test_not_supported_request(client: Client):
    """Test not supported GetCapabilities."""
    # Make a request
    qs = '?SERVICE=ATLAS&REQUEST=Get&MAP={}'.format(PROJECT_FILE)
    rv = client.get(qs, PROJECT_FILE)
    assert rv.status_code == 400

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'
