import json
import logging

LOGGER = logging.getLogger('server')

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

PROJECT_NO_ATLAS = 'france_parts.qgs'
PROJECT_ATLAS_SIMPLE = 'atlas_simple.qgs'


def test_no_template(client):
    """Test missing template name."""
    qs = '?SERVICE=ATLAS&REQUEST=GetPrint&MAP={}'.format(PROJECT_ATLAS_SIMPLE)
    rv = client.get(qs, PROJECT_ATLAS_SIMPLE)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0
    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'
    assert b['message'] == 'ATLAS - Error from the user while generating the PDF: TEMPLATE is required'


def test_no_exp_filter(client):
    """ Test without EXP_FILTER. """
    qs = (
        '?SERVICE=ATLAS&'
        'REQUEST=GetPrint&'
        'MAP={}&TEMPLATE=layout1-atlas'.format(PROJECT_ATLAS_SIMPLE))
    rv = client.get(qs, PROJECT_ATLAS_SIMPLE)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0
    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'
    assert b['message'] == (
        'ATLAS - Error from the user while generating the PDF: EXP_FILTER is mandatory to print an atlas '
        'layout')


def test_invalid_exp_filter(client):
    """ Test with an invalid EXP_FILTER (not well formed). """
    qs = (
        '?SERVICE=ATLAS&'
        'REQUEST=GetPrint&'
        'MAP={}&'
        'TEMPLATE=layout1-atlas&'
        'EXP_FILTER=id in (1, 2'.format(PROJECT_ATLAS_SIMPLE))
    rv = client.get(qs, PROJECT_ATLAS_SIMPLE)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0
    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'
    assert b['message'] == (
        'ATLAS - Error from the user while generating the PDF: Expression is invalid: \n'
        'syntax error, unexpected $end, expecting COMMA or \')\'')


def test_invalid_exp_filter_field(client):
    """ Test with an invalid EXP_FILTER (unknown field). """
    qs = (
        '?SERVICE=ATLAS&'
        'REQUEST=GetPrint&'
        'MAP={}&'
        'TEMPLATE=layout1-atlas&'
        'EXP_FILTER=fakeId in (1, 2)'.format(PROJECT_ATLAS_SIMPLE))
    rv = client.get(qs, PROJECT_ATLAS_SIMPLE)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0
    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'
    assert b['message'] == (
        'ATLAS - Error from the user while generating the PDF: Expression is invalid, eval error: '
        'Column \'fakeId\' not found')


def test_invalid_template(client):
    """ Make a failed request with invalid TEMPLATE (unknown layout). """
    qs = (
        '?SERVICE=ATLAS&'
        'REQUEST=GetPrint&'
        'MAP={}&'
        'TEMPLATE=Fakelayout1-atlas&'
        'EXP_FILTER=id in (1, 2)'.format(PROJECT_ATLAS_SIMPLE))
    rv = client.get(qs, PROJECT_ATLAS_SIMPLE)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0
    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'
    assert b['message'] == (
        'ATLAS - Error from the user while generating the PDF: Layout `Fakelayout1-atlas` not found')


def test_invalid_scale_and_scales(client):
    """ Test that SCALE and SCALES can not be used together."""
    qs = (
        '?SERVICE=ATLAS&'
        'REQUEST=GetPrint&'
        'MAP={}&'
        'TEMPLATE=layout1-atlas&'
        'EXP_FILTER=id in (1, 2)&'
        'SCALE=5000&SCALES=10000,5000'.format(PROJECT_ATLAS_SIMPLE))
    rv = client.get(qs, PROJECT_ATLAS_SIMPLE)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0
    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'
    assert b['message'] == (
        'ATLAS - Error from the user while generating the PDF: SCALE and SCALES can not be used together.')


def test_invalid_scale(client):
    """ Make a failed request with invalid SCALE. """
    qs = (
        '?SERVICE=ATLAS&'
        'REQUEST=GetPrint&'
        'MAP={}&'
        'TEMPLATE=layout1-atlas&'
        'EXP_FILTER=id in (1, 2)&'
        'SCALE=5000n'.format(PROJECT_ATLAS_SIMPLE))
    rv = client.get(qs, PROJECT_ATLAS_SIMPLE)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0
    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'
    assert b['message'] == 'ATLAS - Error from the user while generating the PDF: Invalid number in SCALE.'


def test_invalid_scales(client):
    """ Test a failed request with invalid SCALES. """
    qs = (
        '?SERVICE=ATLAS&'
        'REQUEST=GetPrint&'
        'MAP={}&'
        'TEMPLATE=layout1-atlas&'
        'EXP_FILTER=id in (1, 2)&'
        'SCALES=10000n,5000'.format(PROJECT_ATLAS_SIMPLE))
    rv = client.get(qs, PROJECT_ATLAS_SIMPLE)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0
    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'
    assert b['message'] == 'ATLAS - Error from the user while generating the PDF: Invalid number in SCALES.'


def test_invalid_atlas_layout(client):
    """ Test a failed request on a project without atlas layout. """
    qs = (
        '?SERVICE=ATLAS&'
        'REQUEST=GetPrint&'
        'MAP={}&'
        'TEMPLATE=layout-no-atlas&'
        'EXP_FILTER=id in (1, 2)&'
        'SCALES=10000,5000'.format(PROJECT_NO_ATLAS))
    rv = client.get(qs, PROJECT_NO_ATLAS)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0
    b = json.loads(rv.content.decode('utf-8'))
    assert b['status'] == 'fail'
    assert b['message'] == (
        'ATLAS - Error from the user while generating the PDF: Layout `layout-no-atlas` not found')


def test_valid_getprint_atlas(client):
    """ Test Atlas GetPrint response for atlas. """
    qs = (
        '?SERVICE=ATLAS&'
        'REQUEST=GetPrint&'
        'MAP={}&'
        'TEMPLATE=layout1-atlas&'
        'EXP_FILTER=id in (1, 2)'.format(PROJECT_ATLAS_SIMPLE))
    rv = client.get(qs, PROJECT_ATLAS_SIMPLE)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '') == 'application/pdf'
    assert rv.headers.get('Content-Type', '').find('application/pdf') == 0


def test_valid_getprint_report(client):
    """ Test Atlas GetPrint response for report. """
    qs = (
        '?SERVICE=ATLAS&'
        'REQUEST=GetPrint&'
        'MAP={}&'
        'TEMPLATE=layout2-report&'.format(PROJECT_ATLAS_SIMPLE))
    rv = client.get(qs, PROJECT_ATLAS_SIMPLE)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '') == 'application/pdf'
    assert rv.headers.get('Content-Type', '').find('application/pdf') == 0
