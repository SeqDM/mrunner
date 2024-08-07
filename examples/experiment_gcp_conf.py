# Minimal mrunner experiment configuration
import os

from munch import Munch

from mrunner.experiment import Experiment

if "NEPTUNE_API_TOKEN" not in os.environ or "NEPTUNE_PROJECT_NAME" not in os.environ:
    print("Please set NEPTUNE_API_TOKEN and NEPTUNE_PROJECT_NAME env variables")
    print("Their values can be from up.neptune.ml. Click help and then quickstart.")
    exit(1)

exp = Experiment(
    name="Basic experiment",
    script="python3 experiment_basic.py",
    project=os.environ["NEPTUNE_PROJECT_NAME"],
    tags=["test_experiments"],
    env={
        "NEPTUNE_API_TOKEN": os.environ["NEPTUNE_API_TOKEN"],
        "PYTHON_PATH": "$PYTHONPATH:.",
    },
    parameters=Munch(param1=10),
)

# A specification file must contain list of experiments in experiments_list variable. Here just one.
experiments_list = [exp]
