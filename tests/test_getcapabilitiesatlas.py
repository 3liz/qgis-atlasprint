import json
import logging

LOGGER = logging.getLogger('server')

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'

PROJECT_FILE = 'no_atlas.qgs'


def test_atlas_metadata(client):
    """ Test plugin metadata using service WMS and ATLAS. """
    urls = [
        '?SERVICE=ATLAS&REQUEST=GetCapabilities&MAP={}'.format(PROJECT_FILE),
        '?SERVICE=WMS&REQUEST=GetCapabilitiesAtlas&MAP={}'.format(PROJECT_FILE)
    ]
    for url in urls:
        rv = client.get(url, PROJECT_FILE)
        assert rv.status_code == 200

        assert rv.headers.get('Content-Type', '').find('application/json') == 0

        b = json.loads(rv.content.decode('utf-8'))
        assert b['status'] == 'success'

        assert 'metadata' in b
        assert 'name' in b['metadata']
        assert b['metadata']['name'] == 'atlasprint'
        assert 'version' in b['metadata']
