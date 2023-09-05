import importlib


def import_class(qualname: str):
    """Dynamically imports class from a qualified name

    Args:
        qualname: fully qualified class name including package name,
         e.g. ``core.state_manager.StateManager``

    Returns:
        imported class
    """
    module_name, class_name = qualname.rsplit(".", maxsplit=1)
    klass = getattr(importlib.import_module(module_name), class_name)
    return klass
