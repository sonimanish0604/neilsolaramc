from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes import admin
from app.main import app


@dataclass
class InMemoryStore:
    tenants_by_name: dict[str, SimpleNamespace] = field(default_factory=dict)
    users_by_id: dict[str, SimpleNamespace] = field(default_factory=dict)
    users_by_firebase_uid: dict[str, SimpleNamespace] = field(default_factory=dict)
    roles: dict[tuple[str, str], SimpleNamespace] = field(default_factory=dict)
    audit_logs: list[dict] = field(default_factory=list)


class FakeDB:
    def commit(self) -> None:
        return None


def _seed_store() -> InMemoryStore:
    store = InMemoryStore()
    tenant = SimpleNamespace(
        id=uuid4(),
        name="Seed Tenant",
        plan_code="TRIAL",
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
    )
    store.tenants_by_name[tenant.name] = tenant

    user = SimpleNamespace(
        id=uuid4(),
        tenant_id=tenant.id,
        firebase_uid="seed-user-1",
        name="Seed User",
        email="seed@example.com",
        phone=None,
        status="ACTIVE",
    )
    store.users_by_id[str(user.id)] = user
    store.users_by_firebase_uid[user.firebase_uid] = user

    role = SimpleNamespace(id=uuid4(), tenant_id=tenant.id, user_id=user.id, role="OWNER")
    store.roles[(str(user.id), role.role)] = role
    return store


def _install_admin_mocks(store: InMemoryStore) -> None:
    fake_db = FakeDB()
    app.dependency_overrides[admin.get_admin_session] = lambda: fake_db

    def get_tenant_by_name(_: FakeDB, tenant_name: str):
        return store.tenants_by_name.get(tenant_name)

    def create_tenant(_: FakeDB, payload):
        tenant = SimpleNamespace(
            id=uuid4(),
            name=payload.name,
            plan_code=payload.plan_code,
            status=payload.status,
            created_at=datetime.now(timezone.utc),
        )
        store.tenants_by_name[tenant.name] = tenant
        return tenant

    def get_user_by_firebase_uid(_: FakeDB, firebase_uid: str):
        return store.users_by_firebase_uid.get(firebase_uid)

    def create_user(_: FakeDB, payload):
        user = SimpleNamespace(
            id=uuid4(),
            tenant_id=payload.tenant_id,
            firebase_uid=payload.firebase_uid,
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            status=payload.status,
        )
        store.users_by_id[str(user.id)] = user
        store.users_by_firebase_uid[user.firebase_uid] = user
        return user

    def get_user_by_id(_: FakeDB, user_id):
        return store.users_by_id.get(str(user_id))

    def get_user_role(_: FakeDB, user_id, role: str):
        return store.roles.get((str(user_id), role))

    def create_user_role(_: FakeDB, tenant_id, user_id, role: str):
        user_role = SimpleNamespace(id=uuid4(), tenant_id=tenant_id, user_id=user_id, role=role)
        store.roles[(str(user_id), role)] = user_role
        return user_role

    def write_audit_log(_: FakeDB, actor, action, entity_type, entity_id, tenant_id=None, metadata=None):
        store.audit_logs.append(
            {
                "actor": actor,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "tenant_id": str(tenant_id) if tenant_id else None,
                "metadata": metadata or {},
            }
        )

    admin._get_tenant_by_name = get_tenant_by_name
    admin._create_tenant = create_tenant
    admin._get_user_by_firebase_uid = get_user_by_firebase_uid
    admin._create_user = create_user
    admin._get_user_by_id = get_user_by_id
    admin._get_user_role = get_user_role
    admin._create_user_role = create_user_role
    admin._write_audit_log = write_audit_log


def test_admin_create_tenant_sunny_day():
    store = _seed_store()
    _install_admin_mocks(store)
    client = TestClient(app)

    res = client.post(
        "/admin/tenants",
        headers={"X-Admin-Key": "dev-bootstrap-key"},
        json={"name": "Noggin Solar", "plan_code": "TRIAL", "status": "ACTIVE"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Noggin Solar"
    assert len(store.audit_logs) == 1
    assert store.audit_logs[0]["action"] == "TENANT_CREATED"


def test_admin_create_tenant_rainy_duplicate():
    store = _seed_store()
    _install_admin_mocks(store)
    client = TestClient(app)

    res = client.post(
        "/admin/tenants",
        headers={"X-Admin-Key": "dev-bootstrap-key"},
        json={"name": "Seed Tenant", "plan_code": "TRIAL", "status": "ACTIVE"},
    )

    assert res.status_code == 409


def test_admin_create_user_sunny_day():
    store = _seed_store()
    _install_admin_mocks(store)
    client = TestClient(app)
    tenant = store.tenants_by_name["Seed Tenant"]

    res = client.post(
        "/admin/users",
        headers={"X-Admin-Key": "dev-bootstrap-key"},
        json={
            "tenant_id": str(tenant.id),
            "firebase_uid": "new-user-22",
            "name": "New User",
            "email": "new@example.com",
            "phone": "9999999999",
            "status": "ACTIVE",
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["firebase_uid"] == "new-user-22"
    assert len(store.audit_logs) == 1
    assert store.audit_logs[0]["action"] == "USER_CREATED"


def test_admin_create_user_rainy_duplicate_firebase_uid():
    store = _seed_store()
    _install_admin_mocks(store)
    client = TestClient(app)
    tenant = store.tenants_by_name["Seed Tenant"]

    res = client.post(
        "/admin/users",
        headers={"X-Admin-Key": "dev-bootstrap-key"},
        json={
            "tenant_id": str(tenant.id),
            "firebase_uid": "seed-user-1",
            "name": "Another User",
            "status": "ACTIVE",
        },
    )

    assert res.status_code == 409


def test_admin_assign_role_sunny_day():
    store = _seed_store()
    _install_admin_mocks(store)
    client = TestClient(app)
    user_id = next(iter(store.users_by_id.keys()))

    res = client.post(
        f"/admin/users/{user_id}/roles",
        headers={"X-Admin-Key": "dev-bootstrap-key"},
        json={"role": "SUPERVISOR"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["role"] == "SUPERVISOR"
    assert len(store.audit_logs) == 1
    assert store.audit_logs[0]["action"] == "ROLE_ASSIGNED"


def test_admin_assign_role_rainy_invalid_role():
    store = _seed_store()
    _install_admin_mocks(store)
    client = TestClient(app)
    user_id = next(iter(store.users_by_id.keys()))

    res = client.post(
        f"/admin/users/{user_id}/roles",
        headers={"X-Admin-Key": "dev-bootstrap-key"},
        json={"role": "INVALID_ROLE"},
    )

    assert res.status_code == 400


def test_admin_assign_role_rainy_user_not_found():
    store = _seed_store()
    _install_admin_mocks(store)
    client = TestClient(app)

    res = client.post(
        f"/admin/users/{uuid4()}/roles",
        headers={"X-Admin-Key": "dev-bootstrap-key"},
        json={"role": "OWNER"},
    )

    assert res.status_code == 404


def test_admin_requires_admin_key():
    store = _seed_store()
    _install_admin_mocks(store)
    client = TestClient(app)

    res = client.post("/admin/tenants", json={"name": "No Key Tenant", "plan_code": "TRIAL", "status": "ACTIVE"})
    assert res.status_code == 401

