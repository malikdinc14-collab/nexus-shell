import unittest
from unittest.mock import MagicMock, patch
import uuid
import json
import os
import sys

# Add core to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.internal.daemon import NexusDaemon, BaseContainerAdapter

class MockAdapter(BaseContainerAdapter):
    def __init__(self):
        self.focused = "%0"
        self.containers = {"%0": {"role": None, "geo": {"w": 80, "h": 24}}}
        self.metadata = {}

    def get_focused_id(self): return self.focused
    def swap_containers(self, s, t): return True
    def select_container(self, t): self.focused = t; return True
    def container_exists(self, t): return t in self.containers
    def set_metadata(self, t, k, v): 
        if t not in self.metadata: self.metadata[t] = {}
        self.metadata[t][k] = v
        return True
    def get_metadata(self, t, k): return self.metadata.get(t, {}).get(k)
    def get_geometry(self, t): return self.containers.get(t, {}).get("geo")
    def set_geometry(self, t, g): 
        if t in self.containers: self.containers[t]["geo"] = g

class TestNexusDaemon(unittest.TestCase):
    def setUp(self):
        # Mock State Engine
        self.patcher = patch('state_engine.NexusStateEngine')
        self.mock_state = self.patcher.start()()
        self.mock_state.get.return_value = {"stacks": {}}
        
        self.daemon = NexusDaemon()
        self.daemon.adapter = MockAdapter()
        self.daemon.state_engine = self.mock_state

    def tearDown(self):
        self.patcher.stop()

    def test_get_or_create_stack(self):
        # Test creation of a new stack for an anonymous pane
        sid, stack = self.daemon._get_or_create_stack("local", initial_pane="%0")
        self.assertTrue(sid.startswith("stack_"))
        self.assertEqual(len(stack["tabs"]), 1)
        self.assertEqual(stack["tabs"][0]["id"], "%0")

    def test_op_push(self):
        # Push a new pane (%1) into a stack
        self.daemon.adapter.containers["%1"] = {"geo": {"w": 80, "h": 24}}
        res = self.daemon.handle_stack_op("push", {"role": "editor", "pane_id": "%1", "name": "Tool"})
        self.assertEqual(res["status"], "ok")
        
        sid, stack = self.daemon._get_stack_by_identity("editor")
        self.assertEqual(len(stack["tabs"]), 2)
        self.assertEqual(stack["tabs"][1]["id"], "%1")
        self.assertEqual(stack["active_index"], 1)

    def test_op_switch(self):
        # Setup stack with 2 tabs
        self.daemon.adapter.containers["%1"] = {"geo": {"w": 80, "h": 24}}
        self.daemon.handle_stack_op("push", {"role": "editor", "pane_id": "%1"})
        
        # Switch back to index 0
        res = self.daemon.handle_stack_op("switch", {"role": "editor", "index": 0})
        self.assertEqual(res["status"], "ok")
        
        sid, stack = self.daemon._get_stack_by_identity("editor")
        self.assertEqual(stack["active_index"], 0)
        self.assertEqual(stack["tabs"][0]["status"], "VISIBLE")
        self.assertEqual(stack["tabs"][1]["status"], "BACKGROUND")

    def test_op_tag(self):
        sid, stack = self.daemon._get_or_create_stack("editor", initial_pane="%0")
        res = self.daemon.handle_stack_op("tag", {"role": "editor", "tag": "feature-x"})
        self.assertEqual(res["status"], "ok")
        
        _, stack = self.daemon._get_stack_by_identity("feature-x")
        self.assertIn("feature-x", stack["tags"])

    def test_geometry_preservation(self):
        # Push with geometry
        self.daemon.adapter.containers["%1"] = {"geo": {"w": 40, "h": 12}}
        self.daemon.handle_stack_op("push", {"role": "editor", "pane_id": "%1"})
        
        # Change geometry of visible pane (%1)
        self.daemon.adapter.set_geometry("%1", {"w": 100, "h": 50})
        
        # Switch to %0
        self.daemon.handle_stack_op("switch", {"role": "editor", "index": 0})
        
        # Verify %1's geometry was captured
        _, stack = self.daemon._get_stack_by_identity("editor")
        self.assertEqual(stack["tabs"][1]["geometry"], {"w": 100, "h": 50})

    def test_teleportation_collision(self):
        """Verify that pushing to a role stays local even if the role exists elsewhere."""
        # 0. Register Pane %1 in adapter so it isn't scrubbed
        self.daemon.adapter.containers["%1"] = {"geo": {"w": 80, "h": 24}}
        self.daemon.adapter.containers["%2"] = {"geo": {"w": 80, "h": 24}}
        self.daemon.adapter.containers["%99"] = {"geo": {"w": 80, "h": 24}}

        # 1. Setup Pane %1 as the existing Editor
        self.daemon.adapter.get_metadata = MagicMock()
        self.daemon.adapter.get_focused_id = MagicMock()
        
        # Simulate Pane %1 already having the 'stack_editor' identity
        self.daemon.adapter.get_metadata.side_effect = lambda pid, key: "stack_editor" if pid == "%1" and key == "@nexus_stack_id" else None
        sid1, stack1 = self.daemon._get_or_create_stack("editor", initial_pane="%1")
        # Ensure it's in the registry
        self.daemon.registry["stack_editor"] = stack1
        
        # 2. Setup Pane %2 as a fresh container calling 'push editor'
        # We simulate the Orchestrator NOT setting @nexus_stack_id yet (returns None for %2)
        # We override the side_effect to return None for %2 so it's anonymous
        self.daemon.adapter.get_metadata.side_effect = lambda pid, key: None 
        self.daemon.adapter.get_focused_id.return_value = "%2"
        
        # Perform push from Pane %2
        res = self.daemon.handle_stack_op("push", {"role": "editor", "pane_id": "%99"})
        
        # Assertions
        new_sid = res.get("stack_id")
        self.assertNotEqual(new_sid, "stack_editor", "Teleportation detected! Pushed into remote stack_editor.")
        
        # Verify both stacks exist independently in the registry
        # stack_editor should still be there because %1 exists
        self.assertIn("stack_editor", self.daemon.registry)
        self.assertIn(new_sid, self.daemon.registry)
        self.assertEqual(self.daemon.registry[new_sid]["role"], "editor")

if __name__ == "__main__":
    unittest.main()
