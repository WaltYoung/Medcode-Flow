from __future__ import annotations

import importlib
import logging
import pkgutil

import app.workflows as workflows_pkg

logger = logging.getLogger(__name__)


def discover_workflows() -> None:
    """Import all app.workflows.* packages so they self-register."""
    package_path = workflows_pkg.__path__
    prefix = workflows_pkg.__name__ + "."
    for module in pkgutil.iter_modules(package_path, prefix):
        name = module.name.rsplit(".", 1)[-1]
        if name.startswith("_"):
            continue
        importlib.import_module(module.name)
        logger.info("discovered_workflow_module module=%s", module.name)
