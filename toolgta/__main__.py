"""AUTO GTA5VN v5.0 — Entry Point

Run the application with:
    python -m toolgta

Or directly:
    python toolgta/__main__.py
"""
from __future__ import annotations

from .utils import setup_logger
from .constants import APP_VERSION


def main() -> None:
    """Initialise logger, check templates, and launch the main GUI."""
    logger = setup_logger()
    logger.info('=' * 40)
    logger.info('AUTO GTA5VN v%s starting', APP_VERSION)
    logger.info('=' * 40)

    # Ensure templates exist (download from GitHub if missing)
    from .template_downloader import ensure_templates
    if not ensure_templates():
        logger.warning(
            'Templates missing! Copy E/, F/, Y/ folders '
            'next to the program or check internet connection.'
        )

    from .gui.app import AutoGTAApp
    app = AutoGTAApp()
    app.mainloop()


if __name__ == '__main__':
    main()
