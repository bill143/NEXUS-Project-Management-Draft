"""DDC PDF→Excel permission definitions."""

from app.core.permissions import Role, permission_registry


def register_ddc_pdf_excel_permissions() -> None:
    permission_registry.register_module_permissions(
        "ddc_pdf_excel",
        {
            "ddc_pdf_excel.extract": Role.EDITOR,
        },
    )
