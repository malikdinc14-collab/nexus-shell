import sys
import json
import subprocess
from abc import ABC, abstractmethod

class PickerAdapter(ABC):
    @abstractmethod
    def pick(self, context, items_json):
        """
        Takes context string and a list of JSON-string items.
        Returns the selected JSON-string or None.
        """
        pass

    def _parse_selected(self, selected_line):
        """Helper to ensure we return a valid JSON string."""
        if not selected_line:
            return None
        try:
            return json.loads(selected_line)
        except json.JSONDecodeError:
            return None
