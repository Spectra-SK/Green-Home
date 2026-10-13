"""Customer memory manager for the GreenHome advisor.

Stores permitted customer preferences, budget constraints, completed retrofits,
and recommendation history using synthetic demo data only.

Ensures customer context never overrides deterministic physics calculations or
invents numerical estimates.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_FILE = (
    Path(__file__).resolve().parent.parent / "customer_memory.json"
)

# Permitted top-level profile fields
PERMITTED_PROFILE_FIELDS = {
    "customer_id",
    "property_id",
    "budget_limit_gbp",
    "preferences",
    "completed_retrofits",
    "recommendation_history",
}

# Forbidden sensitive fields to prevent accidental PII/secret storage
FORBIDDEN_KEY_PATTERNS = {
    "api_key",
    "password",
    "secret",
    "token",
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "bank_account",
    "email",
    "phone",
}


def _contains_forbidden_keys(data: Any) -> bool:
    """Recursively check whether data contains any forbidden/sensitive keys."""
    if isinstance(data, dict):
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(pattern in k_lower for pattern in FORBIDDEN_KEY_PATTERNS):
                return True
            if _contains_forbidden_keys(v):
                return True
    elif isinstance(data, list):
        for item in data:
            if _contains_forbidden_keys(item):
                return True
    return False


def validate_customer_profile(profile: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate a single customer profile dict."""
    if not isinstance(profile, dict):
        return False, "Customer profile must be a dictionary."

    customer_id = profile.get("customer_id")
    if not customer_id or not isinstance(customer_id, str):
        return False, "Missing or invalid customer_id."

    if _contains_forbidden_keys(profile):
        return False, "Profile contains forbidden sensitive keys (PII or secrets)."

    # Check budget type if present
    budget = profile.get("budget_limit_gbp")
    if budget is not None and not isinstance(budget, (int, float)):
        return False, "budget_limit_gbp must be a number or null."

    # Check completed retrofits type if present
    completed = profile.get("completed_retrofits")
    if completed is not None and not isinstance(completed, list):
        return False, "completed_retrofits must be a list."

    # Check preferences type if present
    prefs = profile.get("preferences")
    if prefs is not None and not isinstance(prefs, dict):
        return False, "preferences must be a dictionary."

    return True, None


def validate_customer_memory(data: Any) -> tuple[bool, str | None]:
    """Validate customer memory file content."""
    if not isinstance(data, dict):
        return False, "Customer memory must be a JSON object."

    customers = data.get("customers")
    if customers is None:
        return True, None

    if not isinstance(customers, dict):
        return False, "'customers' field must be a dictionary."

    for cust_id, profile in customers.items():
        valid, err = validate_customer_profile(profile)
        if not valid:
            return False, f"Invalid profile for customer '{cust_id}': {err}"

    return True, None


def load_customer_memory(file_path: Path | str | None = None) -> dict[str, Any]:
    """Load customer memory from JSON file.

    Handles missing or malformed files gracefully by returning an empty memory store.
    """
    target = Path(file_path) if file_path else DEFAULT_MEMORY_FILE

    if not target.exists():
        logger.warning("Customer memory file %s does not exist. Returning empty store.", target)
        return {"customers": {}}

    try:
        with open(target, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {"customers": {}}
            data = json.loads(content)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to parse customer memory file %s: %s. Returning empty store.", target, e)
        return {"customers": {}}

    is_valid, err = validate_customer_memory(data)
    if not is_valid:
        logger.warning("Customer memory validation failed: %s. Returning empty store.", err)
        return {"customers": {}}

    if "customers" not in data:
        data["customers"] = {}

    return data


def save_customer_memory(
    data: dict[str, Any],
    file_path: Path | str | None = None,
) -> bool:
    """Save customer memory to JSON file after validation."""
    is_valid, err = validate_customer_memory(data)
    if not is_valid:
        logger.error("Cannot save invalid customer memory: %s", err)
        raise ValueError(f"Invalid customer memory data: {err}")

    target = Path(file_path) if file_path else DEFAULT_MEMORY_FILE
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except OSError as e:
        logger.error("Failed to write customer memory file %s: %s", target, e)
        return False


def get_customer_profile(
    customer_id: str,
    file_path: Path | str | None = None,
) -> dict[str, Any] | None:
    """Retrieve a specific customer profile by ID."""
    memory = load_customer_memory(file_path=file_path)
    return memory.get("customers", {}).get(customer_id)


def update_customer_profile(
    customer_id: str,
    updates: dict[str, Any],
    file_path: Path | str | None = None,
) -> dict[str, Any]:
    """Update or create a customer profile in customer memory."""
    memory = load_customer_memory(file_path=file_path)
    customers = memory.setdefault("customers", {})

    existing = customers.get(customer_id, {"customer_id": customer_id})
    merged = {**existing, **updates, "customer_id": customer_id}

    is_valid, err = validate_customer_profile(merged)
    if not is_valid:
        raise ValueError(f"Profile update validation failed: {err}")

    customers[customer_id] = merged
    save_customer_memory(memory, file_path=file_path)
    return merged
