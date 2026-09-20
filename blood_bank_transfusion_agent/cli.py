"""Installed command-line entry point for the canonical transfusion tools."""

from cli import main

__all__ = ["main"]

if __name__ == "__main__":
    raise SystemExit(main())
