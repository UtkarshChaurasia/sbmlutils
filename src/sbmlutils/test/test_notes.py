"""Test notes which could be """
import re

import libsbml
import pytest

from sbmlutils.factory import Parameter
from sbmlutils.notes import Notes


def test_markdown_note():
    p = Parameter(
        "p1",
        value=1.0,
        notes="""
        # Markdown note
        Test this *text* in this `variable`.

            notes = Notes(c.notes)

        ## Heading 2
        <https://example.com>

        <img src="./test.png" />
        """,
    )
    doc = libsbml.SBMLDocument()
    model: libsbml.Model = doc.createModel()
    sbml_p: libsbml.Parameter = p.create_sbml(model)

    print("\n")
    print("-" * 80)
    print(p.notes)
    print("-" * 80)
    notes = Notes(p.notes)
    print(notes)
    print("-" * 80)
    sbml_notes = sbml_p.getNotesString()
    print("-" * 80)

    assert '<a href="https://example.com">https://example.com</a>' in sbml_notes
    assert "<h2>Heading 2</h2>" in sbml_notes
    assert '<img src="./test.png"/>' in sbml_notes


notes_data = [
    # headings
    ("# test", "<h1>test</h1>"),
    ("## test", "<h2>test</h2>"),
    ("### test", "<h3>test</h3>"),
    ("#### test", "<h4>test</h4>"),
    ("##### test", "<h5>test</h5>"),
    ("###### test", "<h6>test</h6>"),
    # emphasize
    ("*asterisks*", r"<p>[.\s]*<em>asterisks</em>[s\s]*</p>"),
    ("_underscore_", r"<p>[\s]*<em>underscore</em>[\s]*</p>"),
    ("**asterisks**", r"<p>[\s]*<strong>asterisks</strong>[\s]*</p>"),
    ("__underscores__", r"<p>[\s]*<strong>underscores</strong>[\s]*</p>"),
    ("<p>test</p>", "<p>test</p>"),
    # lists
    (
        """
    1. First item
    2. Second item
    """,
        "<ol>[\s]*<li>First item</li>[\s]*<li>Second item</li>[\s]*</ol>",
    ),
    (
        """
    * First item
    * Second item
    """,
        "<ul>[\s]*<li>First item</li>[\s]*<li>Second item</li>[\s]*</ul>",
    ),
    (
        """
    - item
    """,
        "<ul>[\s]*<li>item</li>[\s]*</ul>",
    ),
    (
        """
    + item
    """,
        "<ul>[\s]*<li>item</li>[\s]*</ul>",
    ),
]


@pytest.mark.parametrize("note,expected", notes_data)
def test_note(note: str, expected: str):
    note = Notes(note)
    note_str = str(note)
    print(expected)
    print(note_str)
    match = re.search(pattern=expected, string=note_str)
    assert match
