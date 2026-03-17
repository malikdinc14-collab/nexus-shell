#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import json

# Add core/api to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "core/api"))
from intent_resolver import IntentResolver

def test_resolver():
    resolver = IntentResolver()
    
    test_cases = [
        ("run", "ROLE", "explorer", "push", "terminal"),
        ("run", "ROLE", "explorer", "swap", "menu"),
        ("run", "PLACE", "/tmp", "push", "terminal"),
        ("run", "PROJECT", "/Users/Shared/nexus", "replace", "terminal"),
        ("run", "MODEL", "gpt-4", "push", "terminal"),
        ("run", "ACTION", ":workspace dev", "push", "terminal"),
        ("run", "ACTION", "ls -la", "replace", "terminal"),
    ]
    
    print(f"{'TYPE':<10} | {'PAYLOAD':<20} | {'STRATEGY':<15} | {'ROLE':<10}")
    print("-" * 65)
    
    for verb, itype, payload, intent, caller in test_cases:
        plan = resolver.resolve(verb, itype, payload, intent, caller)
        print(f"{itype:<10} | {payload:<20} | {plan['strategy']:<15} | {plan['role']:<10}")

if __name__ == "__main__":
    test_resolver()
