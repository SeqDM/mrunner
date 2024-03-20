def get_by_name(name):
    if name == "print_neptune_link":
        from mrunner.plugins import neptune_link

        return neptune_link.print_neptune_link

    raise RuntimeWarning(
        rf"Plugin {name} not found. Please remove it from the callback list."
    )
