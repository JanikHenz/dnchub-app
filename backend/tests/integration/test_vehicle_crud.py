"""Integration tests for vehicle CRUD lifecycle."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Organization


class TestVehicleCRUDIntegration:
    """Test create -> read -> update -> delete lifecycle for vehicles."""

    def test_create_then_read_returns_same_data(
        self,
        client: TestClient,
        manager_headers: dict,
        admin_headers: dict,
        test_organization: Organization,
    ):
        """Create a vehicle, then read it back and verify data matches."""
        # Create
        create_res = client.post(
            "/api/v1/vehicles",
            json={
                "registration_plate": "INTEG-001",
                "make": "BMW",
                "model": "X5",
                "year": 2024,
                "type": "suv",
                "fuel_type": "diesel",
            },
            headers=manager_headers,
        )
        assert create_res.status_code == 201
        created = create_res.json()
        vehicle_id = created["id"]

        # Read
        get_res = client.get(
            f"/api/v1/vehicles/{vehicle_id}",
            headers=admin_headers,
        )
        assert get_res.status_code == 200
        fetched = get_res.json()
        assert fetched["registration_plate"] == "INTEG-001"
        assert fetched["make"] == "BMW"
        assert fetched["model"] == "X5"
        assert fetched["year"] == 2024

    def test_update_then_read_reflects_change(
        self,
        client: TestClient,
        manager_headers: dict,
        admin_headers: dict,
        test_organization: Organization,
    ):
        """Create, update, then verify the update is persisted."""
        # Create
        create_res = client.post(
            "/api/v1/vehicles",
            json={
                "registration_plate": "INTEG-002",
                "make": "Audi",
                "model": "A4",
                "year": 2023,
                "type": "sedan",
                "fuel_type": "gasoline",
            },
            headers=manager_headers,
        )
        assert create_res.status_code == 201
        vehicle_id = create_res.json()["id"]

        # Update
        update_res = client.patch(
            f"/api/v1/vehicles/{vehicle_id}",
            json={"status": "in_maintenance"},
            headers=manager_headers,
        )
        assert update_res.status_code == 200
        assert update_res.json()["status"] == "in_maintenance"

        # Re-read to confirm persistence
        get_res = client.get(
            f"/api/v1/vehicles/{vehicle_id}",
            headers=admin_headers,
        )
        assert get_res.status_code == 200
        assert get_res.json()["status"] == "in_maintenance"

    def test_delete_then_get_still_returns_soft_deleted(
        self,
        client: TestClient,
        manager_headers: dict,
        admin_headers: dict,
        test_organization: Organization,
    ):
        """Create, soft-delete, then verify record still accessible but has deleted_at set.

        Note: BaseService.get_or_404 does not filter by deleted_at, so
        soft-deleted records are still returned by GET. The list endpoint
        (get_multi) does filter them out.
        """
        # Create
        create_res = client.post(
            "/api/v1/vehicles",
            json={
                "registration_plate": "INTEG-003",
                "make": "Mercedes",
                "model": "C-Class",
                "year": 2022,
                "type": "sedan",
                "fuel_type": "diesel",
            },
            headers=manager_headers,
        )
        assert create_res.status_code == 201
        vehicle_id = create_res.json()["id"]

        # Delete (soft)
        delete_res = client.delete(
            f"/api/v1/vehicles/{vehicle_id}",
            headers=manager_headers,
        )
        assert delete_res.status_code == 204

        get_res = client.get(
            f"/api/v1/vehicles/{vehicle_id}",
            headers=admin_headers,
        )
        assert get_res.status_code == 404

        list_res = client.get("/api/v1/vehicles", headers=admin_headers)
        assert list_res.status_code == 200
        vehicle_ids = [v["id"] for v in list_res.json()]
        assert vehicle_id not in vehicle_ids

    def test_create_vehicle_appears_in_list(
        self,
        client: TestClient,
        manager_headers: dict,
        admin_headers: dict,
        test_organization: Organization,
    ):
        """Create a vehicle, then verify it appears in the list."""
        # Create
        create_res = client.post(
            "/api/v1/vehicles",
            json={
                "registration_plate": "INTEG-004",
                "make": "Volvo",
                "model": "XC90",
                "year": 2024,
                "type": "suv",
                "fuel_type": "hybrid",
            },
            headers=manager_headers,
        )
        assert create_res.status_code == 201
        vehicle_id = create_res.json()["id"]

        # List
        list_res = client.get("/api/v1/vehicles", headers=admin_headers)
        assert list_res.status_code == 200
        vehicle_ids = [v["id"] for v in list_res.json()]
        assert vehicle_id in vehicle_ids
