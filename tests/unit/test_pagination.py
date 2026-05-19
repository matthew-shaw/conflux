import pytest

from app.utils.pagination import page_out_of_range


class DummyPagination:
    def __init__(self, pages: int):
        self.pages = pages


def test_page_out_of_range_allows_page_one_when_zero_pages():
    """
    GIVEN a pagination object reporting zero pages
    WHEN page 1 is requested
    THEN the page is considered in-range (no 404)
    """
    pag = DummyPagination(0)
    assert page_out_of_range(pag, 1) is False


@pytest.mark.parametrize(
    "pages,page,expected",
    [
        (0, 2, True),
        (3, 3, False),
        (3, 4, True),
        (5, 0, True),
        (5, -1, True),
    ],
)
def test_page_out_of_range_variants(pages, page, expected):
    """
    GIVEN various pagination.page counts
    WHEN different pages are requested
    THEN the helper returns the expected boolean
    """
    pag = DummyPagination(pages)
    assert page_out_of_range(pag, page) is expected


def test_page_out_of_range_signals_out_of_range():
    """
    GIVEN a pagination object and an out-of-range page
    WHEN page_out_of_range is called
    THEN it returns True so the caller can abort with 404
    """
    pag = DummyPagination(1)
    assert page_out_of_range(pag, 2) is True
