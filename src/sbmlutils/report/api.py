"""API for the sbmlreport web service.

This provides basic functionality of
parsing the model and returning the JSON representation based on fastAPI.
"""

import json
import logging
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pymetadata.core.annotation import RDFAnnotation, RDFAnnotationData
from pymetadata.identifiers.miriam import BQB

from sbmlutils.report.api_examples import examples_info
from sbmlutils.report.sbmlinfo import SBMLDocumentInfo


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


def _handle_error(e: Exception, info: Optional[Dict] = None) -> Response:
    """Handle exceptions in the backend.

    All calls are wrapped in a try/except which will provide the errors to the frontend.

    :param info: optional dictionary with information.
    """
    logger.error(e)

    res = {
        "errors": [
            f"{e.__str__()}",
            f"{''.join(traceback.format_exception(None, e, e.__traceback__))}",
        ],
        "warnings": [],
        "info": info,
    }

    return Response(content=json.dumps(res), media_type="application/json")


def _render_json_content(content: Dict) -> Response:
    """Render content to JSON."""
    # use minimal dict
    # content = clean_empty(content)
    json_bytes = json.dumps(
        content,
        ensure_ascii=False,
        allow_nan=True,
        indent=0,
        separators=(",", ":"),
    ).encode("utf-8")

    return Response(content=json_bytes, media_type="application/json")


@api.get("/examples")
def examples() -> Response:
    """Get examples for reports."""
    try:
        content = {
            "examples": [
                example["metadata"] for example in examples_info.values()
            ]
        }
        raise ValueError("This is a test error")
        return _render_json_content(content)

    except Exception as e:
        return _handle_error(e)


@api.get("/examples/{example_id}")
def example(example_id: str) -> Response:
    """Get specific example."""
    try:
        example = examples_info.get(example_id, None)
        content: Dict
        if example:
            source: Path = example["file"]  # type: ignore
            content = _content_for_source(source=source)
        else:
            content = {"error": f"example for id does not exist '{example_id}'"}

        return _render_json_content(content)
    except Exception as e:
        return _handle_error(e)


def _content_for_source(source: Path) -> Dict:
    """Create content for given source."""
    try:
        content: Dict[str, Any] = {}
        time_start = time.time()
        info = SBMLDocumentInfo.from_sbml(source=source)
        content["report"] = info.info
        time_elapsed = round(time.time() - time_start, 3)
        logger.warning(f"JSON created for '{source}' in '{time_elapsed}'")
        content["debug"] = {"jsonReportTime": f"{time_elapsed} [s]"}
        return content

    except Exception as e:
        return _handle_error(e)


@api.get("/annotation_resource")
def get_annotation_resource(resource: str) -> Response:
    """Get information for annotation_resource.

    Used to resolve annotation information.

    :param resource: unique identifier of resource (url or miriam urn)
    :return: Response
    """
    try:
        annotation = RDFAnnotation(qualifier=BQB.IS, resource=resource)
        data = RDFAnnotationData(annotation=annotation)
        info = data.to_dict()

        return Response(content=json.dumps(info), media_type="application/json")

    except Exception as e:
        return _handle_error(e)


@api.post("/file")
async def report_from_file(request: Request) -> Response:
    """Upload file and return JSON report."""
    try:
        file_data = await request.form()
        file_content = await file_data["source"].read()
        content = _write_to_file_and_generate_report("temp_model.xml", file_content, "wb")

        return _render_json_content(content)

    except Exception as e:
        return _handle_error(e)


@api.get("/url")
def report_from_url(url: str) -> Response:
    """Get JSON report via URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        file_content = response.text
        content = _write_to_file_and_generate_report("temp_sbml.xml", file_content, "w")
        return Response(content=json.dumps(content), media_type="application/json")

    except Exception as e:
        return _handle_error(e)


@api.post("/content")
async def get_report_from_content(request: Request) -> Response:
    """Get JSON report from file contents."""
    try:
        file_content = await request.body()
        filename = "sbml_file.xml"
        content = _write_to_file_and_generate_report(filename, file_content, "wb")
        return Response(content=json.dumps(content), media_type="application/json")

    except Exception as e:
        return _handle_error(e)


def _write_to_file_and_generate_report(
    filename: str, file_content: str, mode: str
) -> Dict:
    """Write file content to temporary file and generate report."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / filename
        with open(path, mode) as sbml_file:
            sbml_file.write(file_content)
            content = _content_for_source(source=path)

    return content


if __name__ == "__main__":
    # shell command: uvicorn sbmlutils.report.api:app --reload --port 1444
    uvicorn.run(
        "sbmlutils.report.api:api",
        host="localhost",
        port=1444,
        log_level="info",
        reload=True,
    )
