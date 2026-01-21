"""Test core functions."""


from qgis.core import QgsVectorLayer

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


def test_global_scales():
    """Test we can fetch global scales from INI file or hardcoded scales."""
    from atlasprint.core import global_scales

    scales = global_scales()
    expected = [
        1000000, 500000, 250000, 100000, 50000, 25000, 10000, 5000, 2500, 1000, 500
    ]
    assert scales == expected


def test_slugify():
    """ Test to slugify a string. """
    from atlasprint.core import clean_string
    assert clean_string('I\'m Ä safe l@yoùt NÀMÉ') == 'Im_A_safe_lyout_NAME'


def test_optimize_filter():
    """Test we can optimize the feature filter if $id."""
    from atlasprint.core import optimize_expression

    # No primary key
    layer = QgsVectorLayer('None?field=primary:integer&field=name:string(20)', 'test', 'memory')

    assert 'abc' == optimize_expression(layer, 'abc')
    assert '$id=3' == optimize_expression(layer, '$id=3')
    assert "$id in ('1','2')" == optimize_expression(layer, "$id in ('1','2')")

    # One primary key
    layer.primaryKeyAttributes = lambda: [0]

    assert '"primary"=3' == optimize_expression(layer, '$id=3')
    assert '"primary" in (\'1\',\'2\')' == optimize_expression(layer, "$id in ('1','2')")

    # Two primary keys
    layer.primaryKeyAttributes = lambda: [0, 1]
    assert '$id=3' == optimize_expression(layer, '$id=3')

    # One primary key type string
    layer = QgsVectorLayer('None?field=primary:string(20)&field=name:string(20)', 'test', 'memory')
    layer.primaryKeyAttributes = lambda: [0]
    assert '"primary"=3' == optimize_expression(layer, '$id=3')

    # One primary key type double
    layer = QgsVectorLayer('None?field=primary:double(20,20)&field=name:string(20)', 'test', 'memory')
    layer.primaryKeyAttributes = lambda: [0]
    assert '"primary"=3' == optimize_expression(layer, '$id=3')

    # One primary key type int but not the first attribute of the layer
    layer = QgsVectorLayer('None?field=count:integer&field=primary:integer&field=name:string(20)', 'test', 'memory')
    layer.primaryKeyAttributes = lambda: [1]
    assert '"primary"=3' == optimize_expression(layer, '$id=3')
