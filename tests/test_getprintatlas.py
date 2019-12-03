import sys
import os
import logging
import lxml.etree
import json

from qgis.core import Qgis, QgsProject
from qgis.server import (QgsBufferServerRequest,
                         QgsBufferServerResponse)

LOGGER = logging.getLogger('server')

def test_atlas_getprint_failed(client):
    """  Test getcapabilites response
    """
    projectfile = "france_parts.qgs"

    # Make a failed request no template
    qs = "?SERVICE=ATLAS&REQUEST=GetPrint&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400

    assert rv.headers.get('Content-Type','').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'

    # Make a failed request no EXP_FILTER
    qs = "?SERVICE=ATLAS&REQUEST=GetPrint&MAP=france_parts.qgs&TEMPLATE=Layout1"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400

    assert rv.headers.get('Content-Type','').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'

    # Make a failed request with invalid EXP_FILTER
    qs = "?SERVICE=ATLAS&REQUEST=GetPrint&MAP=france_parts.qgs&TEMPLATE=Layout1&EXP_FILTER=id in (1, 2"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400

    assert rv.headers.get('Content-Type','').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'

    # Make a failed request with invalid EXP_FILTER
    qs = "?SERVICE=ATLAS&REQUEST=GetPrint&MAP=france_parts.qgs&TEMPLATE=Layout1&EXP_FILTER=id in (1, 2)&SCALE=5000&SCALES=10000,5000"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400

    assert rv.headers.get('Content-Type','').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'

    # Make a failed request with invalid SCALE and SCALES (can not be used together)
    qs = "?SERVICE=ATLAS&REQUEST=GetPrint&MAP=france_parts.qgs&TEMPLATE=Layout1&EXP_FILTER=id in (1, 2)&SCALE=5000&SCALES=10000,5000"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400

    assert rv.headers.get('Content-Type','').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'

    # Make a failed request with invalid SCALE
    qs = "?SERVICE=ATLAS&REQUEST=GetPrint&MAP=france_parts.qgs&TEMPLATE=Layout1&EXP_FILTER=id in (1, 2)&SCALE=5000n"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400

    assert rv.headers.get('Content-Type','').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'

    # Make a failed request with invalid SCALES
    qs = "?SERVICE=ATLAS&REQUEST=GetPrint&MAP=france_parts.qgs&TEMPLATE=Layout1&EXP_FILTER=id in (1, 2)&SCALE=10000n,5000"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400

    assert rv.headers.get('Content-Type','').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'

