from flask.testing import FlaskClient


def test_index(test_client: FlaskClient) -> None:
    """GIVEN the application index route WHEN requested THEN the response contains the expected page title."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert b"<title>" in response.data


def test_accessibility(test_client: FlaskClient) -> None:
    """GIVEN the accessibility route WHEN requested THEN the response renders successfully."""
    response = test_client.get("/accessibility")
    assert response.status_code == 200
    assert b"<title>" in response.data


def test_cookies_get(test_client: FlaskClient) -> None:
    """GIVEN the cookies page WHEN requested THEN the response includes default cookie values."""
    response = test_client.get("/cookies")
    assert response.status_code == 200

    assert response.request.cookies.get("functional", "no") == "no"
    assert response.request.cookies.get("analytics", "no") == "no"


def test_http_errors(test_client: FlaskClient) -> None:
    """GIVEN invalid pages WHEN requested THEN the application returns the appropriate HTTP error pages."""
    response = test_client.get("/not-found")
    assert response.status_code == 404
    assert b"Page not found" in response.data

    response = test_client.get("/")
    response = test_client.get("/")
    response = test_client.get("/")
    assert response.status_code == 429
    assert b"There have been too many attempts to access this page." in response.data
