"""isolate - a simple isolation layer that runs commands inside a bubblewrap sandbox.

The public surface is intentionally tiny. Most callers only need the CLI entry
point (`isolate.cli.main`). The building blocks below are exported so tests and
advanced users can assemble a sandbox command without going through the CLI.
"""

__version__ = "0.1.0"
