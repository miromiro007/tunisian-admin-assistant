"""Central logging setup. Call setup_logging() once at startup."""
import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger to print readable lines to stdout."""
    logging.basicConfig(
        # Minimum level to show. .upper() accepts "info" or "INFO".
        level=level.upper(),
        # Line layout, example:
        # 2026-10-09 02:30:12 | INFO | app.main | Starting ...
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        # Date/time layout
        datefmt="%Y-%m-%d %H:%M:%S",
        # Send logs to the console (stdout), which Docker collects
        stream=sys.stdout,
        # Replace handlers configured earlier (for example by uvicorn)
        force=True,
    )