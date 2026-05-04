from flask.testing import FlaskClient


def test_index(client: FlaskClient) -> None:
    """
    Test the index route.

    Args:
        client (FlaskClient): The test client for the Flask application.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert b"<title>" in response.data


def test_accessibility(client: FlaskClient) -> None:
    """
    Test the accessibility route.

    Args:
        client (FlaskClient): The test client for the Flask application.
    """
    response = client.get("/accessibility")
    assert response.status_code == 200
    assert b"<title>" in response.data


def test_cookies_get(client: FlaskClient) -> None:
    """Test the cookies route with a GET request."""
    response = client.get("/cookies")
    assert response.status_code == 200

    # Check default cookie values
    assert response.request.cookies.get("functional", "no") == "no"
    assert response.request.cookies.get("analytics", "no") == "no"


def test_http_errors(client: FlaskClient) -> None:
    """Test handling of HTTP errors."""
    response = client.get("/not-found")
    assert response.status_code == 404
    assert b"Page not found" in response.data

    response = client.get("/")
    response = client.get("/")
    response = client.get("/")
    assert response.status_code == 429
    assert b"There have been too many attempts to access this page." in response.data
