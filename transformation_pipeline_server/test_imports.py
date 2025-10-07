#!/usr/bin/env python
"""
Test script to verify ServiceContainer import consistency
"""
import sys
import os

# Add src directory to path like app.py does
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

print("Testing ServiceContainer imports...")

# Test import as app.py now does it
from shared.services.service_container import ServiceContainer as SC1
print(f"App-style import: ServiceContainer class ID = {id(SC1)}")
print(f"App-style import: _initialized = {SC1._initialized}")

# Test import as routers do it
from shared.services.service_container import ServiceContainer as SC2
print(f"Router-style import: ServiceContainer class ID = {id(SC2)}")
print(f"Router-style import: _initialized = {SC2._initialized}")

# They should be the same class
if SC1 is SC2:
    print("✓ SUCCESS: Both imports reference the same class!")
else:
    print("✗ ERROR: Imports reference different classes!")

print(f"\nFinal check - are they the same object? {SC1 is SC2}")