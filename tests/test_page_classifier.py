import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from page_classifier import PageClassifier
from unittest.mock import MagicMock


def test_get_target_pages():
    classifier = PageClassifier(MagicMock())
    classification = "Introduction: 1, 2\nMethods: 3"

    pages = classifier._get_target_pages(classification, "Introduction")
    assert pages == ["1", "2"]


def test_get_page_content():
    classifier = PageClassifier(MagicMock())
    data = {
        "Page 1": "a",
        "*Page 2*": "b",
        "Page 3:": "c",
    }
    assert classifier._get_page_content("1", data) == "a"
    assert classifier._get_page_content("2", data) == "b"
    assert classifier._get_page_content("3", data) == "c"
