import importlib.util
from typing import List, Optional
from ...base import MenuCapability

class TextualMenuAdapter(MenuCapability):
    """
    Implementation of MenuCapability using the 'textual' Python library.
    This adapter dynamically checks for textual so it remains an optional dependency.
    """

    @property
    def capability_type(self):
        from ...base import CapabilityType
        return CapabilityType.MENU

    @property
    def capability_id(self): return "textual"

    def is_available(self) -> bool:
        return importlib.util.find_spec("textual") is not None

    def show_menu(self, options: List[str], prompt: str = "Select:") -> Optional[str]:
        if not options:
            return None
            
        # Due to Textual's async nature and full-screen event loop, 
        # invoking it inline inside a synchronous prompt is complex.
        # Typically, we launch a secondary nxm.py script or run it in a subprocess
        # returning the output. For this architecture stub, we'll return the first option.
        # TODO: Implement full Textual App overlay integration here, removing external dependencies
        try:
            return options[0]
        except Exception:
            return None
