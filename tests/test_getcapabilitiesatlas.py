import sys
import os
import logging
import lxml.etree
import json

from qgis.core import Qgis, QgsProject
from qgis.server import (QgsBufferServerRequest,
                         QgsBufferServerResponse)

LOGGER = logging.getLogger('server')

def test_atlas_getcapabilities(client):
    """  Test getcapabilites response
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=ATLAS&REQUEST=GetCapabilities&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type','').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'success'

    assert ('metadata' in b)
    assert ('name' in b['metadata'])
    assert b['metadata']['name'] == 'atlasprint'
    assert ('version' in b['metadata'])

def test_getcapabilitiesatlas(client):
    """  Test getcapabilites response
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=WMS&REQUEST=GetCapabilitiesAtlas&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type','').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'success'

    assert ('metadata' in b)
    assert ('name' in b['metadata'])
    assert b['metadata']['name'] == 'atlasprint'
    assert ('version' in b['metadata'])

