import argparse
import ast
import atexit
import datetime
import logging
import os
import re
import socket

import cloudpickle
from munch import Munch

experiment_ = None
logger_ = logging.getLogger(__name__)


def inject_dict_to_gin(dict, scope=None):
    import gin

    gin_bindings = []
    for key, value in dict.items():
        if key == "imports":
            for module_str in value:
                binding = f"import {module_str}"
                gin_bindings.append(binding)
            continue

        if isinstance(value, str) and not value[0] in ("@", "%", "{", "(", "["):
            binding = f'{key} = "{value}"'
        else:
            binding = f"{key} = {value}"
        gin_bindings.append(binding)

    gin.parse_config(gin_bindings)


def nest_params(params, prefixes):
    """Nest params based on keys prefixes.

    Example:
      For input
      params = dict(
        param0=value0,
        prefix0_param1=value1,
        prefix0_param2=value2
      )
      prefixes = ("prefix0_",)
      This method modifies params into nested dictionary:
      {
        "param0" : value0
        "prefix0": {
          "param1": value1,
          "param2": value2
        }
      }
    """
    for prefix in prefixes:
        dict_params = Munch()
        l_ = len(prefix)
        for k in list(params.keys()):
            if k.startswith(prefix):
                dict_params[k[l_:]] = params.pop(k)
        params[prefix[:-1]] = dict_params


def get_configuration(
    print_diagnostics=False,
    with_neptune=False,
    inject_parameters_to_gin=False,
    nesting_prefixes=(),
    env_to_properties_regexp=".*PWD",
    config_file=None,
    inject_parameters_to_FLAGS=False,
):
    # with_neptune might be also an id of an experiment
    global experiment_

    if config_file is None:
        parser = argparse.ArgumentParser(description="Debug run.")
        parser.add_argument("--ex", type=str, default="")
        parser.add_argument("--config", type=str, default="")
        commandline_args = parser.parse_args()

        params = None
        experiment = None
        git_info = None

        # This is here for running locally, load experiment from spec
        if commandline_args.ex:
            from path import Path

            vars_ = {"script": str(Path(commandline_args.ex).name)}
            exec(open(commandline_args.ex).read(), vars_)
            experiments = vars_["experiments_list"]
            logger_.info(
                "The specifcation file contains {} "
                "experiments configurations. The first one will be used.".format(
                    len(experiments)
                )
            )
            experiment = experiments[0]
            params = experiment.parameters

    configuration = None
    if config_file is not None:
        configuration = config_file
    elif commandline_args.config:
        configuration = commandline_args.config

    # This is here for running remotely, load experiment from dump
    if configuration is not None:
        logger_.info("File to load:{}".format(configuration))
        with open(configuration, "rb") as f:
            experiment = Munch(cloudpickle.load(f))
        params = Munch(experiment["parameters"])
        git_info = experiment.get("git_info", None)
        if git_info:
            git_info.commit_date = datetime.datetime.now()

    if inject_parameters_to_gin:
        logger_.info("The parameters of the form 'aaa.bbb' will be injected to gin.")
        gin_params = {
            param_name: params[param_name] for param_name in params if "." in param_name
        }
        inject_dict_to_gin(gin_params)

    if with_neptune:
        if "NEPTUNE_API_TOKEN" not in os.environ:
            logger_.warning(
                "Neptune will be not used.\nTo run with neptune please set your NEPTUNE_API_TOKEN variable"
            )
        else:
            import neptune

            params_to_sent_to_neptune = {}
            for param_name in params:
                try:
                    val = str(params[param_name])
                    if val.isnumeric():
                        val = ast.literal_eval(val)
                    params_to_sent_to_neptune[param_name] = val
                except Exception:
                    logger_.warning(
                        "Not possible to send to neptune: %s. Implement __str__",
                        param_name,
                    )

            # Set pwd property with path to experiment.
            properties = {
                key: os.environ[key]
                for key in os.environ
                if re.match(env_to_properties_regexp, key)
            }

            if isinstance(with_neptune, str):
                experiment_ = neptune.init_run(
                    project=experiment.project,
                    with_id=with_neptune,
                )
            else:
                experiment_ = neptune.init_run(
                    project=experiment.project,
                    name=experiment.name,
                    tags=experiment.tags,
                )
                experiment_["parameters"] = params
                experiment_["properties"] = properties
                # TODO: How to properly pass git info?
                experiment_["git_info"] = git_info

            atexit.register(experiment_.stop)

    if print_diagnostics:
        logger_.info("PYTHONPATH: %s", os.environ.get("PYTHONPATH", "not_defined"))
        logger_.info("cd %s", os.getcwd())
        logger_.info(socket.getfqdn())
        logger_.info("Params: %s", str(params))

    if inject_parameters_to_FLAGS:
        # absl is required to handle program flags, but can be not installed
        try:
            from absl import flags
        except ImportError as e:
            logger_.error("Install 'absl-py' to use inject_parameters_to_FLAGS option.")
            raise e

        FLAGS = flags.FLAGS
        for p in params:
            setattr(FLAGS, p, params[p])

    if config_file is None:
        nest_params(params, nesting_prefixes)
        if experiment_:
            params["experiment_id"] = experiment_["sys/id"].fetch()
        else:
            params["experiment_id"] = None

    return params


def logger(m, v):
    global experiment_

    if experiment_:
        from PIL import Image

        m = m.lstrip().rstrip()  # This is to circumvent neptune's bug
        experiment_[m].log(v)

    else:
        print("{}:{}".format(m, v))
