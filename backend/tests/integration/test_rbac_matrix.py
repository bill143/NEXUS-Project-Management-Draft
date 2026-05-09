"""Integration test: RBAC matrix.

Validates role-based access control enforced by the FastAPI router across
a representative sample of endpoints. One row per (method, path, role),
asserting the expected HTTP status code. Anonymous (no token) is tested
explicitly via the ``"anonymous"`` pseudo-role.

The expected-status table is the test contract — any drift in the auth
layer surfaces here before merge.

Surfaced by the QA audit at C:/dev/NEXUS-Project-Management-Draft/QA_REPORT.md
(Item 4 recommendation: recurring CI check for RBAC enforcement). Sampled
in the audit by hand against four endpoints; this codifies the same
matrix and is run automatically by the existing ``pytest`` step in
.github/workflows/ci.yml.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Boot the full app once per test (lifespan = module discovery)."""
    app = create_app()

    @asynccontextmanager
    async def lifespan_ctx():
        async with app.router.lifespan_context(app):
            yield

    async with lifespan_ctx():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


async def _register_bootstrap_admin(client: AsyncClient) -> str:
    """Register the first user; bootstrap-first-admin promotes them to admin.

    Per ``UserRepository.has_admin``, an empty users table (no real-domain
    admin) routes the next public registration to ``role='admin'`` so a
    fresh install always has a way in. Conftest creates a per-session
    temp SQLite DB, so this is always the bootstrap path.
    """
    email = f"rbac-admin-{uuid.uuid4().hex[:8]}@hardening.io"
    password = "RbacMatrix123Test"
    reg = await client.post(
        "/api/v1/users/auth/register/",
        json={"email": email, "password": password, "full_name": "RBAC Admin"},
    )
    reg.raise_for_status()
    assert reg.json()["role"] == "admin", (
        "bootstrap-first-admin policy did not fire — fresh DB but role != admin. "
        "Check UserRepository.has_admin filter."
    )
    login = await client.post(
        "/api/v1/users/auth/login/",
        json={"email": email, "password": password},
    )
    login.raise_for_status()
    return login.json()["access_token"]


async def _admin_create_user(client: AsyncClient, admin_token: str, role: str) -> str:
    """Create a user with the requested role via ``POST /api/v1/users/``."""
    email = f"rbac-{role}-{uuid.uuid4().hex[:8]}@hardening.io"
    password = "RbacMatrix123Test"
    headers = {"Authorization": f"Bearer {admin_token}"}
    create = await client.post(
        "/api/v1/users/",
        json={
            "email": email,
            "password": password,
            "full_name": f"RBAC {role.title()}",
            "role": role,
            "is_active": True,
        },
        headers=headers,
    )
    create.raise_for_status()
    login = await client.post(
        "/api/v1/users/auth/login/",
        json={"email": email, "password": password},
    )
    login.raise_for_status()
    return login.json()["access_token"]


@pytest_asyncio.fixture
async def role_tokens(client: AsyncClient) -> dict[str, str | None]:
    """Mint a token for each canonical role + ``None`` for anonymous baseline."""
    admin = await _register_bootstrap_admin(client)
    manager = await _admin_create_user(client, admin, "manager")
    editor = await _admin_create_user(client, admin, "editor")
    viewer = await _admin_create_user(client, admin, "viewer")
    return {
        "admin": admin,
        "manager": manager,
        "editor": editor,
        "viewer": viewer,
        "anonymous": None,
    }


# ── Matrix ─────────────────────────────────────────────────────────────────
# Format: (method, path, role, expected_status_codes_set).
# A set of acceptable codes lets us tolerate non-RBAC reasons (e.g. 422 on
# malformed-but-authorized bodies) without falsely failing on auth posture.
#
# The contract:
#   * 401 → no/invalid token
#   * 403 → valid token, insufficient role
#   * 200/422 → request reached the handler (auth passed); 422 means body
#               validation, not RBAC, so it's an acceptable "auth OK" code.

RBAC_MATRIX: list[tuple[str, str, str, set[int]]] = [
    # GET /users/me/ — authenticated read of own profile (any role allowed)
    ("GET", "/api/v1/users/me/", "admin", {200}),
    ("GET", "/api/v1/users/me/", "manager", {200}),
    ("GET", "/api/v1/users/me/", "editor", {200}),
    ("GET", "/api/v1/users/me/", "viewer", {200}),
    ("GET", "/api/v1/users/me/", "anonymous", {401}),
    # GET /users/ — list users (admin & manager allowed; editor & viewer denied)
    ("GET", "/api/v1/users/", "admin", {200}),
    ("GET", "/api/v1/users/", "manager", {200}),
    ("GET", "/api/v1/users/", "editor", {403}),
    ("GET", "/api/v1/users/", "viewer", {403}),
    ("GET", "/api/v1/users/", "anonymous", {401}),
    # GET /projects/ — list projects (any role allowed)
    ("GET", "/api/v1/projects/", "admin", {200}),
    ("GET", "/api/v1/projects/", "manager", {200}),
    ("GET", "/api/v1/projects/", "editor", {200}),
    ("GET", "/api/v1/projects/", "viewer", {200}),
    ("GET", "/api/v1/projects/", "anonymous", {401}),
]


# ── Test ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rbac_matrix(
    client: AsyncClient,
    role_tokens: dict[str, str | None],
) -> None:
    """Walk the matrix in one test invocation.

    Single-test design (vs. ``pytest.mark.parametrize``) is intentional:
    parametrizing this matrix re-runs the fixture chain — boot app + mint
    five accounts — for every row, which both balloons the test runtime
    AND triggers an aiosqlite/event-loop-teardown race that surfaces as
    ``RuntimeError: Event loop is closed`` on every row after the first.
    Running the matrix once inside a single async test sidesteps both
    problems while still giving per-row failure detail via the
    accumulating ``failures`` list.
    """
    failures: list[str] = []

    for method, path, role, expected in RBAC_MATRIX:
        headers: dict[str, str] = {}
        token = role_tokens[role]
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"

        response = await client.request(method, path, headers=headers)

        if response.status_code not in expected:
            failures.append(
                f"  {method} {path} as {role}: expected one of "
                f"{sorted(expected)}, got {response.status_code} "
                f"(body: {response.text[:120]!r})"
            )

    assert not failures, (
        f"\nRBAC matrix violations ({len(failures)}/{len(RBAC_MATRIX)}):\n"
        + "\n".join(failures)
    )
