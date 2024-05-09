Plugins that can be used in ``specification_helper.py`` as callbacks.


### Example usage of ```print_neptune_link```
```
"""experiment config"""

from mrunner.helpers.specification_helper import create_experiments_helper

experiments_list = create_experiments_helper(
    experiment_name="Fake experiment",
    base_config={...},
    params_grid={},
    script="fake script",
    "...."
    project_name="pmtest/bison-pl",

    callbacks=["print_neptune_link"]
)
```
**For developers:** if you want your plugin to be accessible by name you need to register it in ```__init__.py```

### Available plugins
```print_neptune_link``` prints a link to the future neptune experiment
