# -*- coding: utf-8 -*-
import logging
import re
from typing import Any, Generator

import attr
import cloudpickle
from attrs import Factory, define, field
from path import Path

from mrunner.utils.namesgenerator import get_random_name, get_unique_name
from mrunner.utils.utils import WrapperCmd

LOGGER = logging.getLogger(__name__)


@define(kw_only=True)
class ContextBase:
    backend_type: str
    context_name: str
    storage_dir: Path
    cmd: WrapperCmd = None
    cwd: Path = Factory(Path.getcwd)


def values_to_str(d: dict[str, Any]) -> dict[str, str]:
    return {k: str(v) for k, v in d.items()}


@define(kw_only=True, slots=False)
class Experiment(object):

    project: str = field()
    name: Any = field()
    script: Any = field()
    parameters: Any = field()
    env: dict[str, str] = field(factory=dict, converter=values_to_str)
    paths_to_copy: Any = field(factory=list)
    tags: Any = field(factory=list)
    exclude: Any = field(factory=list)
    random_name: Any = field(factory=get_random_name)
    unique_name: Any = field(default=attr.Factory(get_unique_name, takes_self=True))
    git_info: Any = field(default=None)
    with_mpi: Any = field(default=False)
    restore_from_path: Any = field(default=None)
    send_code: Any = field(default=True)

    def to_dict(self):
        return attr.asdict(self)


def _merge_experiment_parameters(cli_kwargs, context):
    config = context.copy()
    for k, v in cli_kwargs.items():
        if k not in config:
            LOGGER.debug('New config["{}"]: {}'.format(k, v))
            config[k] = v
        else:
            if isinstance(config[k], (list, tuple)):
                LOGGER.debug(
                    'Extending config["{}"]: {} with {}'.format(k, config[k], v)
                )
                if isinstance(v, (list, tuple)):
                    config[k].extend(v)
                else:
                    config[k].append(v)
            else:
                LOGGER.debug(
                    'Overwriting config["{}"]: {} -> {}'.format(k, config[k], v)
                )
                config[k] = v
    return config


def _load_py_experiment(script, spec, *, dump_dir: Path):
    LOGGER.info(
        "Found {} function in {}; will use it as experiments configuration generator".format(
            spec, script
        )
    )

    def _create_and_dump_config(spec_params, dump_dir: Path, idx: int):
        config_path = dump_dir / f"config_{idx}"
        with open(config_path, "wb") as file:
            cloudpickle.dump(spec_params, file, protocol=4)

        return config_path

    experiments_list = get_experiments_list(script, spec)
    for idx, experiment in enumerate(experiments_list):
        spec_params = experiment.to_dict()
        spec_params["name"] = re.sub(r"[ .,_:;-]+", "-", spec_params["name"].lower())

        config_path = _create_and_dump_config(spec_params, dump_dir, idx)

        yield config_path, spec_params


def generate_experiments(
    script: str, context: dict, *, spec="spec", dump_dir=None
) -> Generator[tuple[str, dict], Any, None]:
    experiments = _load_py_experiment(script, spec=spec, dump_dir=dump_dir)

    for config_path, spec_params in experiments:
        experiment = _merge_experiment_parameters(spec_params, context)
        yield config_path, experiment


_experiment_list = None


def get_experiments_list(script, spec):
    global _experiment_list
    if _experiment_list is None:
        vars = {
            "script": str(Path(script).name),
            "__file__": str(Path(script)),
        }
        exec(open(script).read(), vars)
        _experiment_list = vars.get(spec, None)
        if _experiment_list is None:
            print(
                "The experiment file was loaded but the {} "
                "variable is not set. Exiting".format(spec)
            )
            exit(1)

    return _experiment_list
