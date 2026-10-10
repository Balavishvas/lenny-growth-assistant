from fastapi.testclient import TestClient

from app.main import app


def test_workspace_homepage_is_served():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Lenny — Editorial Growth Intelligence" in response.text
    assert 'id="messageInput"' in response.text


def test_frontend_assets_are_served():
    with TestClient(app) as client:
        css_response = client.get("/static/styles.css")
        js_response = client.get("/static/app.js")

    assert css_response.status_code == 200
    assert ".workspace-grid" in css_response.text
    assert js_response.status_code == 200
    assert "function sendMessage" in js_response.text
