import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import os
from yaml_metadata_generator import YamlMetadataGenerator
from unittest.mock import MagicMock


def test_extract_metadata_from_intro():
    mock_api = MagicMock()
    mock_api.generate_content.return_value = "My Title\nJohn Doe\nProf. Advisor"
    gen = YamlMetadataGenerator(mock_api)
    metadata = gen.extract_metadata_from_intro("intro text")
    assert metadata == {
        'title': 'My Title',
        'author': 'John Doe',
        'advisor': 'Prof. Advisor'
    }
