# Usually instead of defining spec function manually it is easier to use create_experiments_spec.
import os

from mrunner.helpers.specification_helper import create_experiments_helper

if "NEPTUNE_API_TOKEN" not in os.environ or "NEPTUNE_PROJECT_NAME" not in os.environ:
    print("Please set NEPTUNE_API_TOKEN and NEPTUNE_PROJECT_NAME env variables")
    print("Their values can be from up.neptune.ml. Click help and then quickstart.")
    exit()

base_config = dict(param1=10)
params_grid = {"LinearFunction.coefficient": [1.0, 2.0]}

experiments_list = create_experiments_helper(
    experiment_name="Gin experiment",
    project_name=os.environ["NEPTUNE_PROJECT_NAME"],
    script="python experiment_gin.py",
    python_path=".",
    tags=["whoami", "gin", "beautiful_project"],
    base_config=base_config,
    params_grid=params_grid,
)
