from tests.test_refills import VALID, payload


def submit_three(client):
    ids = []
    for n in range(3):
        response = client.post("/refills", json=payload(prescription_number=f"RX-{n:04d}"))
        assert response.status_code == 201
        ids.append(response.json()["id"])
    return ids


def test_list_is_newest_first_and_includes_customer(client, auth_headers):
    first, second, third = submit_three(client)

    response = client.get("/refills", headers=auth_headers)

    assert response.status_code == 200
    items = response.json()
    assert [item["id"] for item in items] == [third, second, first]
    assert items[0]["customer"]["phone"] == "+2349031234567"
    assert items[0]["prescription_number"] == "RX-0002"


def test_filter_by_status(client, auth_headers):
    first, second, third = submit_three(client)
    client.patch(f"/refills/{second}", json={"status": "ready"}, headers=auth_headers)

    ready = client.get("/refills?status=ready", headers=auth_headers).json()
    new = client.get("/refills?status=new", headers=auth_headers).json()

    assert [item["id"] for item in ready] == [second]
    assert [item["id"] for item in new] == [third, first]
    assert client.get("/refills?status=bogus", headers=auth_headers).status_code == 422


def test_update_status(client, auth_headers):
    (refill_id, *_) = submit_three(client)

    response = client.patch(f"/refills/{refill_id}", json={"status": "preparing"}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["status"] == "preparing"
    assert response.json()["id"] == refill_id


def test_update_rejects_bad_status_and_unknown_id(client, auth_headers):
    (refill_id, *_) = submit_three(client)

    bad = client.patch(f"/refills/{refill_id}", json={"status": "shipped"}, headers=auth_headers)
    missing = client.patch("/refills/9999", json={"status": "ready"}, headers=auth_headers)

    assert bad.status_code == 422
    assert missing.status_code == 404
