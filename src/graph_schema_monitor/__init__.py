"""Offline Microsoft Graph schema monitor package."""

from .diff import diff_snapshots
from .parser import parse_csdl_file

__all__ = ["diff_snapshots", "parse_csdl_file"]
