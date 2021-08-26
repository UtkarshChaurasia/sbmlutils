"""API for the sbmlreport web service.

This provides basic functionality of
parsing the model and returning the JSON representation based on fastAPI.
"""
import json
import logging
import tempfile
import time
import requests
from pathlib import Path
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from sbmlutils.report.api_examples import examples_info
from sbmlutils.report.sbmlinfo import SBMLDocumentInfo, clean_empty


logger = logging.getLogger(__name__)
api = FastAPI()

# API Permissions Data
origins = ["127.0.0.1", "*"]

api.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _write_to_file_and_generate_report(filename: str, file_content: str, mode: str) -> Dict:
    content = {}
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / filename
        with open(path, mode) as sbml_file:
            sbml_file.write(file_content)
            content = _content_for_source(source=path)
    return content

@api.get("/")
def read_root() -> Dict:
    """Information to be returned by root path of the API."""
    return {"sbmlutils": "sbml4humans"}


@api.post("/sbml")
async def upload_sbml(request: Request) -> Response:
    """Upload SBML file and return JSON report.

    FIXME: support COMBINE archives
    """
    try:
        file_data = await request.form()

        filename = file_data["source"].filename
        file_content = await file_data["source"].read()
        content = _write_to_file_and_generate_report(filename, file_content, "wb")
    except IOError as err:
        logger.error(err)
        content = {"error": "SBML Document could not be parsed."}

    return _render_json_content(content)


@api.get("/examples")
def examples() -> Response:
    """Get sbml4humans example SBML models."""
    api_examples = []
    for example in examples_info.values():
        api_examples.append(example["metadata"])

    content = {"examples": api_examples}
    return _render_json_content(content)


@api.get("/examples/{example_id}")
def example(example_id: str) -> Response:
    """Endpoint to get specific example.

    see `examples`

    E.g. http://127.0.0.1:1444/examples/repressilator -> JSON for repressilator
    :param example_id:
    :return:
    """
    example = examples_info.get(example_id, None)
    content: Dict
    if example:
        source: Path = example["file"]  # type: ignore
        content = _content_for_source(source=source)
    else:
        content = {"error": f"example for id does not exist '{example_id}'"}

    return _render_json_content(content)


def _content_for_source(source: Path) -> Dict:
    """Create content for given source."""
    content: Dict[str, Any] = {}
    try:
        time_start = time.time()
        info = SBMLDocumentInfo.from_sbml(source=source)
        content["report"] = info.info
        time_elapsed = round(time.time() - time_start, 3)
        logger.warning(f"JSON created for '{source}' in '{time_elapsed}'")
        content["debug"] = {"jsonReportTime": f"{time_elapsed} [s]"}

    except IOError as err:
        logger.error(err)
        content = {"error": f"Error creating JSON for '{source}'"}
    return content


def _render_json_content(content: Dict) -> Response:
    """Render content to JSON."""
    # content = clean_empty(content)  # FIXME: use minimal dict
    json_bytes = json.dumps(
        content,
        ensure_ascii=False,
        allow_nan=True,
        indent=0,
        separators=(",", ":"),
    ).encode("utf-8")

    return Response(content=json_bytes, media_type="application/json")


# FOR TESTING OF DUMMY CACHE
REGISTRY = {
    "namespaces": [
        {
            "id": 1,
            "prefix": "dummy_prefix_1",
            "name": "Dummy1",
            "pattern": "^DUMMY1:\\d+$",
            "description": "Dummy description 1",
        },
        {
            "id": 2,
            "prefix": "dummy_prefix_2",
            "name": "Dummy2",
            "pattern": "^DUMMY2:\\d+$",
            "description": "Dummy description 2",
        },
    ],
}

DUMMY_ADDITIONAL_INFO = {
    "term": "Dummy Term",
    "name": "Dummy Name",
    "definition": "This is a dummy definition.",
    "synonyms": ["syn1", "syn2"],
}


@api.get("/resource_info/{resource_id}")
def get_resource_info(resource_id: str) -> Response:
    """Get information for given resource.

    Used to resolve annotation information.

    :param resource_id: unique identifier of resource (url or miriam urn)
    :return: Response
    """
    try:
        resource_id = _normalize_resource_id(resource_id)
        _ = _get_identifier_and_term(resource_id)

        print(DUMMY_ADDITIONAL_INFO)
        return Response(
            content=json.dumps(DUMMY_ADDITIONAL_INFO), media_type="application/json"
        )
    except Exception as e:
        logger.error(e)

        res = {
            "error": e,
        }

        return Response(content=json.dumps(res), media_type="application/json")


def _normalize_resource_id(resource_id: str) -> str:
    resource_id = resource_id.replace("%3A", ":")
    print(resource_id)

    # removing escape characters of the form "%xy"
    for i in range(len(resource_id)):
        c = resource_id[i]
        if c == "%":
            resource_id = resource_id[:i] + resource_id[i + 3 :]
            i -= 1

    return resource_id


def _get_identifier_and_term(resource_id: str) -> Dict:
    parts = resource_id.split(":")

    try:
        if len(parts) >= 3:
            identifier = parts[2]
            term = "_".join(parts[3:])
        else:
            identifier = parts[0]
            term = parts[0]

        return {
            "prefix": identifier.lower(),
            "identifier": identifier.upper(),
            "term": term,
        }
    except Exception:
        # FIXME: this is too broad
        raise ValueError("Resource identifier too short")


@api.get("/model_urls/")
def get_report_from_model_url(url: str) -> Response:
    data = requests.get(url)

    if data.status_code == 200:
        filename = "temp_sbml.xml"
        file_content = data.text
        content = _write_to_file_and_generate_report(filename, file_content, "w")
    else:
        content = {
            "error": "File not found!"
        }

    return Response(content=json.dumps(content), media_type="application/json")


@api.post("/sbml_content")
async def get_report_from_file_contents(request: Request) -> Response:
    file_content = await request.body()
    print(file_content)
    filename = "sbml_file.xml"

    try:
        content = _write_to_file_and_generate_report(filename, file_content, "wb")
    except Exception as e:
        print(e)
        content = {
            "error": "Invalid SBML!"
        }

    print(content)
    return Response(content=json.dumps(content), media_type="application/json")


if __name__ == "__main__":
    # shell command: uvicorn sbmlutils.report.api:app --reload --port 1444
    uvicorn.run(
        "sbmlutils.report.api:api",
        host="localhost",
        port=1444,
        log_level="info",
        reload=True,
    )
