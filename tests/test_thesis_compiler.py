import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import os
from thesis_compiler import ThesisCompiler


def test_get_chapter_files(tmp_path):
    order = ['introduction', 'related works', 'methods']
    compiler = ThesisCompiler()
    compiler.chapter_order = order

    # create files
    (tmp_path / 'introduction_chapter_with_figures.md').write_text('a')
    (tmp_path / 'related_works_chapter_cited.md').write_text('b')
    (tmp_path / 'methods_chapter.md').write_text('c')

    files = compiler.get_chapter_files(str(tmp_path))
    expected = [
        str(tmp_path / 'introduction_chapter_with_figures.md'),
        str(tmp_path / 'related_works_chapter_cited.md'),
        str(tmp_path / 'methods_chapter.md')
    ]
    assert files == expected
