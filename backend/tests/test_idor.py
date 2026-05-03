"""Red/Green-Tests für die IDOR- und Soft-Delete-Schwachstellen aus Issue #5 und #14."""

from uuid import uuid4

from fastapi.testclient import TestClient


def register_account(
    client: TestClient,
    org_name: str,
    email: str,
    password: str,
    name: str,
) -> dict[str, str]:
    """Registriere einen neuen Mandanten und gib die Auth-Header zurück."""

    res = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": org_name,
            "email": email,
            "password": password,
            "first_name": name,
            "last_name": name,
        },
    )
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_accounts(client: TestClient) -> tuple[dict[str, str], dict[str, str]]:
    """Lege zwei unabhängige Mandanten (Opfer, Angreifer) an."""

    mail_tag = uuid4()
    victim_headers = register_account(
        client, "Victim GmbH", f"victim-{mail_tag}@test.ch", "victim1234", "Victim"
    )
    attacker_headers = register_account(
        client, "Attacker AG", f"attacker-{mail_tag}@test.ch", "attacker1234", "Attacker"
    )
    return victim_headers, attacker_headers


def create_vehicle(
    client: TestClient, headers: dict[str, str], plate: str
) -> dict:
    """Lege im Mandanten der übergebenen Auth-Header ein Fahrzeug an."""

    res = client.post(
        "/api/v1/vehicles",
        json={
            "registration_plate": plate,
            "make": "Toyota",
            "model": "Camry",
            "year": 1992,
            "type": "suv",
            "fuel_type": "gasoline",
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def create_employee(
    client: TestClient, headers: dict[str, str], tag: str
) -> dict:
    """Lege im Mandanten der übergebenen Auth-Header einen Mitarbeiter an."""

    res = client.post(
        "/api/v1/employees",
        json={
            "employee_id": f"EMP-{tag}",
            "first_name": "Max",
            "last_name": "Mustermann",
            "email": f"emp-{tag}@test.ch",
            "phone": "+41791234567",
            "license_number": f"LIC-{tag}",
            "license_expiry": "2030-01-01",
            "license_class": "B",
            "hire_date": "2024-01-01",
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


class TestIDOR:
    """Cross-Tenant-Isolation: Der Angreifer darf die Daten des Opfers nicht sehen oder verändern (Issue #5)."""

    def test_get_blocked(self, client: TestClient) -> None:
        """GET auf ein fremdes Fahrzeug muss 404 liefern."""

        victim_headers, attacker_headers = create_accounts(client)
        vid = create_vehicle(client, victim_headers, "VICTIM-001")["id"]

        res = client.get(f"/api/v1/vehicles/{vid}", headers=attacker_headers)
        assert res.status_code == 404

    def test_patch_blocked(self, client: TestClient) -> None:
        """PATCH auf ein fremdes Fahrzeug muss 404 liefern."""

        victim_headers, attacker_headers = create_accounts(client)
        vid = create_vehicle(client, victim_headers, "VICTIM-002")["id"]

        res = client.patch(
            f"/api/v1/vehicles/{vid}",
            json={"make": "Hacked"},
            headers=attacker_headers,
        )
        assert res.status_code == 404

    def test_delete_no_effect(self, client: TestClient) -> None:
        """DELETE auf ein fremdes Fahrzeug darf keinen Seiteneffekt haben."""

        victim_headers, attacker_headers = create_accounts(client)
        vid = create_vehicle(client, victim_headers, "VICTIM-003")["id"]

        res = client.delete(f"/api/v1/vehicles/{vid}", headers=attacker_headers)
        assert res.status_code == 204

        again = client.get(f"/api/v1/vehicles/{vid}", headers=victim_headers)
        assert again.status_code == 200

    def test_list_isolated(self, client: TestClient) -> None:
        """Die Fahrzeugliste des Angreifers enthält keine Fahrzeuge des Opfers."""

        victim_headers, attacker_headers = create_accounts(client)
        vid = create_vehicle(client, victim_headers, "VICTIM-004")["id"]

        res = client.get("/api/v1/vehicles", headers=attacker_headers)
        assert res.status_code == 200
        assert vid not in (row["id"] for row in res.json())

    def test_no_org_leak(self, client: TestClient) -> None:
        """Der 404-Body darf keine ``organization_id`` des Opfers preisgeben."""

        victim_headers, attacker_headers = create_accounts(client)
        vehicle = create_vehicle(client, victim_headers, "VICTIM-005")
        victim_org_id = vehicle["organization_id"]

        res = client.get(f"/api/v1/vehicles/{vehicle['id']}", headers=attacker_headers)
        assert res.status_code == 404
        assert victim_org_id not in res.text


class TestSoftDeleteBypass:
    """Soft-gelöschte Datensätze müssen auch per direkter UUID verschwunden bleiben (Issue #14)."""

    def test_get_gone(self, client: TestClient) -> None:
        """GET auf ein soft-gelöschtes Fahrzeug muss 404 liefern."""

        victim_headers, _ = create_accounts(client)
        vid = create_vehicle(client, victim_headers, "VICTIM-006")["id"]

        client.delete(f"/api/v1/vehicles/{vid}", headers=victim_headers)

        res = client.get(f"/api/v1/vehicles/{vid}", headers=victim_headers)
        assert res.status_code == 404

    def test_patch_gone(self, client: TestClient) -> None:
        """PATCH auf ein soft-gelöschtes Fahrzeug muss 404 liefern."""

        victim_headers, _ = create_accounts(client)
        vid = create_vehicle(client, victim_headers, "VICTIM-007")["id"]

        client.delete(f"/api/v1/vehicles/{vid}", headers=victim_headers)

        res = client.patch(
            f"/api/v1/vehicles/{vid}",
            json={"make": "Ghost"},
            headers=victim_headers,
        )
        assert res.status_code == 404

    def test_list_hidden(self, client: TestClient) -> None:
        """Soft-gelöschte Fahrzeuge tauchen in der Liste nicht mehr auf."""

        victim_headers, _ = create_accounts(client)
        vid = create_vehicle(client, victim_headers, "VICTIM-008")["id"]

        client.delete(f"/api/v1/vehicles/{vid}", headers=victim_headers)

        res = client.get("/api/v1/vehicles", headers=victim_headers)
        assert res.status_code == 200
        assert vid not in (row["id"] for row in res.json())

    def test_double_delete(self, client: TestClient) -> None:
        """Ein zweites DELETE bleibt idempotent. Danach ist das Fahrzeug per GET weg."""

        victim_headers, _ = create_accounts(client)
        vid = create_vehicle(client, victim_headers, "VICTIM-009")["id"]

        for _ in range(2):
            res = client.delete(f"/api/v1/vehicles/{vid}", headers=victim_headers)
            assert res.status_code == 204

        res = client.get(f"/api/v1/vehicles/{vid}", headers=victim_headers)
        assert res.status_code == 404


class TestIDOREmployee:
    """Der Patch in BaseService muss für alle erbenden Services greifen."""

    def test_get_blocked(self, client: TestClient) -> None:
        """Angreifer-GET auf einen fremden Mitarbeiter liefert 404."""
        victim_headers, attacker_headers = create_accounts(client)
        tag = str(uuid4())[:8]
        eid = create_employee(client, victim_headers, tag)["id"]

        res = client.get(f"/api/v1/employees/{eid}", headers=attacker_headers)
        assert res.status_code == 404

    def test_patch_blocked(self, client: TestClient) -> None:
        """Angreifer-PATCH auf einen fremden Mitarbeiter liefert 404."""

        victim_headers, attacker_headers = create_accounts(client)
        tag = str(uuid4())[:8]
        eid = create_employee(client, victim_headers, tag)["id"]

        res = client.patch(
            f"/api/v1/employees/{eid}",
            json={"first_name": "Hacked"},
            headers=attacker_headers,
        )
        assert res.status_code == 404

    def test_list_isolated(self, client: TestClient) -> None:
        """Die Mitarbeiterliste des Angreifers enthält keine fremden Einträge."""

        victim_headers, attacker_headers = create_accounts(client)
        tag = str(uuid4())[:8]
        eid = create_employee(client, victim_headers, tag)["id"]

        res = client.get("/api/v1/employees", headers=attacker_headers)
        assert res.status_code == 200
        assert eid not in (row["id"] for row in res.json())

    def test_soft_delete_gone(self, client: TestClient) -> None:
        """Soft-gelöschter Mitarbeiter verschwindet aus GET und LIST."""
        
        victim_headers, _ = create_accounts(client)
        tag = str(uuid4())[:8]
        eid = create_employee(client, victim_headers, tag)["id"]

        res = client.delete(f"/api/v1/employees/{eid}", headers=victim_headers)
        assert res.status_code == 204

        res = client.get(f"/api/v1/employees/{eid}", headers=victim_headers)
        assert res.status_code == 404

        res = client.get("/api/v1/employees", headers=victim_headers)
        assert eid not in (row["id"] for row in res.json())
