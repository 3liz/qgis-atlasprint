import sys
import os
import logging
import lxml.etree

from qgis.core import Qgis, QgsProject
from qgis.server import (QgsBufferServerRequest,
                         QgsBufferServerResponse)

LOGGER = logging.getLogger('server')

def test_getcapabilitiesatlas(client):
    """  Test getcapabilites response
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=WMS&REQUEST=GetCapabilitiesAtlas&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

