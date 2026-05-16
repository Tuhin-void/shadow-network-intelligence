"""
Shadow Network Intelligence - Reporting Package.

Legacy stub re-export is wrapped so the package imports even if the stub
file path is in flux. Production generators live in
`7_reporting_engine.generators`.
"""
try:
    from .sar.sar_generator import SARGenerator  # type: ignore
except Exception:
    SARGenerator = None  # type: ignore

__all__ = ["SARGenerator"]