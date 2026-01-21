import io
import json
import tempfile

import xml.etree.ElementTree as ET

from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
    Protocol,
    Union,
)
from urllib.parse import urlencode

import lxml.etree

from PIL import Image

from qgis.core import QgsProject
from qgis.server import QgsBufferServerResponse


NAMESPACES = {
    "xlink": "http://www.w3.org/1999/xlink",
    "wms": "http://www.opengis.net/wms",
    "wfs": "http://www.opengis.net/wfs",
    "wcs": "http://www.opengis.net/wcs",
    "ows": "http://www.opengis.net/ows/1.1",
    "gml": "http://www.opengis.net/gml",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


class OWSResponse:
    def __init__(self, resp: QgsBufferServerResponse, output_dir: Path):
        self._resp = resp
        self._xml: Optional[lxml.etree._Element] = None
        self._output = output_dir

    @property
    def xml(self) -> Optional[lxml.etree._Element]:
        if self._xml is None and self._resp.headers().get("Content-Type", "").find("text/xml") == 0:
            self._xml = lxml.etree.fromstring(self.content)
        return self._xml

    @property
    def content(self) -> bytes:
        return bytes(self._resp.body())

    def file(self, extension: str) -> Path:
        _, path = tempfile.mkstemp(
            prefix="test-",
            suffix=f".{extension}",
            dir=str(self._output),
        )
        with open(path, "wb") as f:
            f.write(self.content)
        return Path(path)

    @property
    def status_code(self) -> int:
        return self._resp.statusCode()

    @property
    def headers(self) -> Dict[str, str]:
        return self._resp.headers()

    def xpath(self, path: str) -> Any:
        assert self.xml is not None
        return self.xml.xpath(path, namespaces=NAMESPACES)

    def xpath_text(self, path: str) -> str:
        assert self.xml is not None
        return " ".join(e.text for e in self.xpath(path))


def _build_query_string(params: dict, use_urllib: bool = False) -> str:
    """Build a query parameter from a dictionary."""
    if use_urllib:
        return "?" + urlencode(params)

    query_string = "?"
    for k, v in params.items():
        query_string += f"{k}={v}&"
    return query_string


def _check_request(
    result: OWSResponse,
    content_type: str = "application/json",
    http_code: int = 200,
) -> Optional[Union[dict, ET.Element, Image.Image]]:
    """Check the output and return the content."""
    assert result.status_code == http_code, f"HTTP code {result.status_code}, expected {http_code}"
    assert result.headers.get("Content-Type", "").lower().find(content_type) == 0, f"Headers {result.headers}"

    if content_type in ("application/json", "application/vnd.geo+json", "text/xml"):
        content = result.content.decode("utf-8")

        if content_type in ("application/json", "application/vnd.geo+json"):
            return json.loads(content)

        return ET.fromstring(content)

    if content_type in ("image/png",):
        return Image.open(io.BytesIO(result.content))

    return None


class Client(Protocol):
    @property
    def plugin(self) -> Any: ...
    def get_project_path(self, name: str) -> Path: ...
    def get_project(self, name: str) -> QgsProject: ...
    def get(
        self,
        query: str,
        project: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> OWSResponse: ...
