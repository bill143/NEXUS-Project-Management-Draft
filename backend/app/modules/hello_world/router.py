"""Hello World API routes.

Auto-mounted at ``/api/v1/hello_world/`` by the module loader.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def greet(name: str = "World") -> dict[str, str]:
    """Return a greeting for ``name`` (default ``World``)."""
    return {"message": f"Hello, {name}!"}
