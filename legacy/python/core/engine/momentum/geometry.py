"""Proportional geometry save/restore for pane layouts."""

from typing import Dict, List, Any


def capture_geometry(pane_ids: list, pane_dimensions: dict = None) -> dict:
    """Capture proportional geometry for each pane.

    Parameters
    ----------
    pane_ids:
        List of pane id strings to capture.
    pane_dimensions:
        Mapping of ``pane_id -> {"width": int, "height": int,
        "total_width": int, "total_height": int}``.
        If *None* or a pane is missing, that pane gets 0%/0%.

    Returns
    -------
    dict
        ``{pane_id: {"width_pct": float, "height_pct": float}}``
    """
    if pane_dimensions is None:
        pane_dimensions = {}

    result: Dict[str, Dict[str, float]] = {}
    for pid in pane_ids:
        dims = pane_dimensions.get(pid, {})
        total_w = dims.get("total_width", 0)
        total_h = dims.get("total_height", 0)
        w = dims.get("width", 0)
        h = dims.get("height", 0)

        width_pct = (w / total_w * 100.0) if total_w > 0 else 0.0
        height_pct = (h / total_h * 100.0) if total_h > 0 else 0.0

        result[pid] = {
            "width_pct": round(width_pct, 4),
            "height_pct": round(height_pct, 4),
        }
    return result


def apply_geometry(
    geometry: dict,
    total_width: int,
    total_height: int,
) -> List[Dict[str, Any]]:
    """Compute resize commands from saved proportional geometry.

    Parameters
    ----------
    geometry:
        ``{pane_id: {"width_pct": float, "height_pct": float}}``
    total_width:
        Current terminal width in columns.
    total_height:
        Current terminal height in rows.

    Returns
    -------
    list[dict]
        Each entry: ``{"pane_id": str, "width": int, "height": int}``
    """
    commands: List[Dict[str, Any]] = []
    for pane_id, dims in geometry.items():
        w_pct = dims.get("width_pct", 0.0)
        h_pct = dims.get("height_pct", 0.0)
        w = int(round(w_pct / 100.0 * total_width))
        h = int(round(h_pct / 100.0 * total_height))
        commands.append({"pane_id": pane_id, "width": w, "height": h})
    return commands
