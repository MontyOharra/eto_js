#!/usr/bin/env python3
"""
ETO Transformation Pipeline Server Main Entry Point
"""

import os
import sys

# Import after adding to path
from src.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8090"))
    app.run(host="0.0.0.0", port=port, debug=False)