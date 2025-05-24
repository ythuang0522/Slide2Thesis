import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import os
import tempfile
from main import setup_debug_folder


def test_setup_debug_folder(tmp_path):
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_text("data")

    debug_dir = setup_debug_folder(str(pdf_file))
    assert os.path.isdir(debug_dir)
    assert os.path.basename(debug_dir) == f"{pdf_file.stem}_debug"
