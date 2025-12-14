def test_get_menu(client):
    response = client.get("/menu")
    assert response.status_code == 200
