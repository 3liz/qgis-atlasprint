"""Test core functions."""

import json

from qgis.core import QgsVectorLayer

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

    assert rv.headers.get('Content-Type','').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'


def test_optimize_filter():
    """Test we can optimize the feature filter if $id."""
    from atlasprintServer.core import optimize_expression
    layer = QgsVectorLayer('None?field=primary:integer&field=name:string(20)', 'test', 'memory')

    # No primary key
    assert 'abc' == optimize_expression(layer, 'abc')
    assert '$id=3' == optimize_expression(layer, '$id=3')
    assert "$id in ('1','2')" == optimize_expression(layer, "$id in ('1','2')")

    # One primary key
    def fake_keys():
        return ['primary']
    layer.primaryKeyAttributes = fake_keys

    assert '"primary"=3' == optimize_expression(layer, '$id=3')
    assert '"primary" in (\'1\',\'2\')' == optimize_expression(layer, "$id in ('1','2')")

    # Two primary keys
    def fake_keys():
        return ['primary', 'name']
    layer.primaryKeyAttributes = fake_keys
    assert '$id=3' == optimize_expression(layer, '$id=3')

    layer = QgsVectorLayer('None?field=primary:string(20)&field=name:string(20)', 'test', 'memory')

    # One primary key but it's not integer
    def fake_keys():
        return ['primary']
    layer.primaryKeyAttributes = fake_keys
    assert '$id=3' == optimize_expression(layer, '$id=3')
