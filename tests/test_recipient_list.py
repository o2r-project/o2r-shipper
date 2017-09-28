# pylint: skip-file
import requests
import json

global TEST_HOST
TEST_HOST = 'http://localhost:8087/api/v1/'

class TestRecipientList(object):
    def test_statuscode(self):
        r = requests.get(''.join((TEST_HOST, 'recipient')))
        assert r.status_code == 200, "response status code should be 200"

    def test_content(self):
        r = requests.get(''.join((TEST_HOST, 'recipient')))
        assert '"id": "download"' in r.text, "response should contain download repository"
        assert json.loads(r.text) == {"recipients": [{"id": "download", "label": "Download"}]}, "response should have correct content"
