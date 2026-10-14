from .conftest import signup


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_login_and_duplicate(client):
    signup(client)
    dup = client.post("/auth/register", json={"email": "A@example.com", "password": "password123"})
    assert dup.status_code == 409
    ok = client.post("/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/auth/login", json={"email": "a@example.com", "password": "wrong-password"})
    assert bad.status_code == 401


def test_validation_rejects_weak_input(client):
    assert client.post("/auth/register", json={"email": "nope", "password": "password123"}).status_code == 422
    assert client.post("/auth/register", json={"email": "b@example.com", "password": "short"}).status_code == 422


def test_links_require_auth(client):
    assert client.post("/links", json={"url": "https://example.com"}).status_code == 401
    assert client.get("/links", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_create_and_redirect(client, auth):
    r = client.post("/links", json={"url": "https://example.com/page"}, headers=auth)
    assert r.status_code == 201
    code = r.json()["code"]
    assert len(code) == 7
    hit = client.get(f"/{code}", follow_redirects=False)
    assert hit.status_code == 307
    assert hit.headers["location"] == "https://example.com/page"


def test_custom_code_conflict_and_reserved(client, auth):
    assert client.post("/links", json={"url": "https://a.com", "custom_code": "mine"}, headers=auth).status_code == 201
    assert client.post("/links", json={"url": "https://b.com", "custom_code": "mine"}, headers=auth).status_code == 409
    assert client.post("/links", json={"url": "https://b.com", "custom_code": "auth"}, headers=auth).status_code == 400


def test_invalid_url_rejected(client, auth):
    assert client.post("/links", json={"url": "not-a-url"}, headers=auth).status_code == 422


def test_unknown_code_404(client):
    assert client.get("/doesnotexist", follow_redirects=False).status_code == 404


def test_click_stats_and_listing(client, auth):
    code = client.post("/links", json={"url": "https://example.com"}, headers=auth).json()["code"]
    for _ in range(3):
        client.get(f"/{code}", follow_redirects=False, headers={"user-agent": "pytest"})
    s = client.get(f"/links/{code}/stats", headers=auth).json()
    assert s["total_clicks"] == 3 and sum(d["clicks"] for d in s["per_day"]) == 3
    listing = client.get("/links", headers=auth).json()
    assert listing[0]["clicks"] == 3


def test_users_cannot_access_each_others_links(client, auth):
    code = client.post("/links", json={"url": "https://example.com"}, headers=auth).json()["code"]
    other = signup(client, "other@example.com")
    assert client.get(f"/links/{code}/stats", headers=other).status_code == 404
    assert client.delete(f"/links/{code}", headers=other).status_code == 404
    assert client.get("/links", headers=other).json() == []


def test_delete_removes_link_and_clicks(client, auth):
    code = client.post("/links", json={"url": "https://example.com"}, headers=auth).json()["code"]
    client.get(f"/{code}", follow_redirects=False)
    assert client.delete(f"/links/{code}", headers=auth).status_code == 204
    assert client.get(f"/{code}", follow_redirects=False).status_code == 404
