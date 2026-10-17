
from schemas.tool_contract import (
    ToolContract,
    build_parallel_order_contract,
)


def build_registry() -> dict[str, ToolContract]:
    """Return the registered tool contracts."""

    contract = build_parallel_order_contract()
    return {contract.name: contract}


def get_tool(
    name: str,
    registry: dict[str, ToolContract] | None = None,
) -> ToolContract | None:
    """Look up a tool by its registered name."""

    if registry is None:
        registry = build_registry()

    return registry.get(name)
