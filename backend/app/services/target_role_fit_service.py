from app.db.models import TargetRole
from app.schemas.profile import RoleFamily

PRODUCT_FAMILIES: set[str] = {
    "ai_product",
    "fintech_product",
    "data_product",
    "strategy_product",
    "platform_product",
    "growth_product",
    "general_product",
    "product_operations",
}
PRIORITY_TO_FIT = {
    "primary": "Primary",
    "secondary": "Secondary",
    "exploratory": "Exploratory",
}
FIT_ORDER = {"Primary": 3, "Secondary": 2, "Exploratory": 1}


class TargetRoleFitService:
    VERSION = "target-role-fit-v1"

    def evaluate(self, role_family: RoleFamily, target_roles: list[TargetRole]) -> str:
        if role_family == "unknown" or not target_roles:
            return "Unknown"
        exact = [
            PRIORITY_TO_FIT[item.priority]
            for item in target_roles
            if item.role_family == role_family and item.role_family != "unknown"
        ]
        if exact:
            return max(exact, key=lambda item: FIT_ORDER[item])
        target_families = {
            item.role_family for item in target_roles if item.role_family != "unknown"
        }
        if not target_families:
            return "Unknown"
        if role_family in PRODUCT_FAMILIES and target_families & PRODUCT_FAMILIES:
            return "Low"
        if role_family not in PRODUCT_FAMILIES and target_families <= PRODUCT_FAMILIES:
            return "NotTarget"
        return "Low"
