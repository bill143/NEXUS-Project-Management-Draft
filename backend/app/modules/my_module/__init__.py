"""My Module — example community module showing the full backend layout."""


async def on_startup() -> None:
    """Module startup hook — register permissions and validation rules."""
    from app.modules.my_module.permissions import register_my_module_permissions
    from app.modules.my_module.validators import register_my_module_rules

    register_my_module_permissions()
    register_my_module_rules()
