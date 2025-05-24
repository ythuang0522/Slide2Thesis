import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import os
from figure_generator import FigureGenerator
from unittest.mock import MagicMock


def test_read_chapter_content_priority(tmp_path):
    gen = FigureGenerator(MagicMock())
    (tmp_path / 'intro_chapter_cited.md').write_text('cited')
    (tmp_path / 'intro_chapter.md').write_text('orig')

    # with_figures has highest priority
    (tmp_path / 'intro_chapter_with_figures.md').write_text('withfig')
    content = gen.read_chapter_content(str(tmp_path), 'intro')
    assert content == 'withfig'

    # remove with_figures -> should read cited
    (tmp_path / 'intro_chapter_with_figures.md').unlink()
    content = gen.read_chapter_content(str(tmp_path), 'intro')
    assert content == 'cited'

    # remove cited -> should read orig
    (tmp_path / 'intro_chapter_cited.md').unlink()
    content = gen.read_chapter_content(str(tmp_path), 'intro')
    assert content == 'orig'
