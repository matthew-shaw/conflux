from flask_sqlalchemy.pagination import Pagination


def page_out_of_range(pagination: Pagination, page: int) -> bool:
    """Return True if the requested page is outside the available range.

    Behaviour:
    - Always allow page 1 even when there are zero total pages (empty result set).
    - Treat any page < 1 as out of range.
    - If the pagination reports multiple pages, allow pages up to that value.
    """
    try:
        max_page = max(1, int(pagination.pages))
    except Exception:
        # If pagination.pages is not available for any reason, be conservative
        # and allow only page 1.
        max_page = 1

    return page < 1 or page > max_page
