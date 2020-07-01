import copy
import os
import pathlib
import warnings
from collections import Mapping, OrderedDict
from itertools import product
from typing import List

from munch import Munch
from neptune.utils import get_git_info
from termcolor import colored

from mrunner.experiment import Experiment
from mrunner.utils.namesgenerator import get_random_name


def create_experiments_helper(experiment_name: str, base_config: dict, params_grid: dict,
                              script: str, python_path: str, tags: List[str],
                              add_random_tag: bool = True, env: dict = None,
                              project_name: str = None, exclude_git_files: bool = True,
                              exclude: List[str] = None, with_neptune: bool = True,
                              display_neptune_link: bool = True, copy_neptune_link: bool = True,
                              paths_to_dump: str = None, paths_to_copy: List[str] = None,
                              with_mpi: bool = False, callbacks: list = None):

    assert with_neptune == True or project_name is not None, \
        "You need to specify `project_name` if `with_neptune` is False!"

    env = env if env is not None else {}
    exclude = exclude if exclude is not None else []
    callbacks = callbacks if callbacks is not None else []

    random_name = get_random_name()
    if add_random_tag:
        tags.append(random_name)

    if paths_to_dump:
        warnings.warn(
            "paths_to_dump is deprecated, use paths_to_copy instead",
            DeprecationWarning
        )
        paths_to_copy = paths_to_dump.split(' ')

    if python_path:
        env['PYTHONPATH'] = ':'.join(['$PYTHONPATH', ] + python_path.split(':'))

    if with_neptune:
        if "NEPTUNE_API_TOKEN" in os.environ:
            env["NEPTUNE_API_TOKEN"] = os.environ["NEPTUNE_API_TOKEN"]
        elif "NEPTUNE_API_TOKEN_" in os.environ:  # This is if we want to avoid setting the token for other applications
            env["NEPTUNE_API_TOKEN"] = os.environ["NEPTUNE_API_TOKEN_"]
        else:
            print("NEPTUNE_API_TOKEN is not set. Connecting with neptune will fail.")
            display_neptune_link = False

        if project_name is None:
            assert "NEPTUNE_PROJECT_NAME" in os.environ, "You should either set NEPTUNE_PROJECT_NAME or directly pass " \
                                                         "the requested project name. The former is better in the collaborative work" \
                                                         "with many projects"
            project_name = os.environ.get("NEPTUNE_PROJECT_NAME")

        if display_neptune_link:
            link = f'https://ui.neptune.ai/o/pmtest/org/football/experiments?viewId=standard-view&sortBy=%5B%22timeOfCreation%22%5D&sortDirection=%5B%22descending%22%5D&sortFieldType=%5B%22native%22%5D&trashed=false&tags=%5B%22{random_name}%22%5D&lbViewUnpacked=true'
            if copy_neptune_link:
                import pyperclip
                # Fix for systems without copy/paste mechanism (like singularity container).
                try:
                    pyperclip.copy(link)
                except pyperclip.PyperclipException:
                    print("[!] Wasn't able to copy Neptune link! Catched PyperclipException.")

            print("> ============ ============ ============ Neptune link ============ ============ ============ <")
            print(colored(link, 'green'))
            print("> ============ ============ ============ Neptune link ============ ============ ============ <")

    params_configurations = get_combinations(params_grid)
    print(colored(f"Will run {len(params_configurations)} experiments", 'red'))
    experiments = []

    git_info = None
    if exclude_git_files:
        exclude += [".git", ".gitignore", ".gitmodules"]
        git_info = get_git_info(".")
        if git_info:
            # Hack due to external bugs
            git_info.commit_date = None

    # Last chance to change something
    for callback in callbacks:
        callback(**locals())
    for params_configuration in params_configurations:
        config = copy.deepcopy(base_config)
        config.update(params_configuration)
        config = Munch(config)

        experiments.append(Experiment(project=project_name, name=experiment_name, script=script,
                                      parameters=config, paths_to_copy=paths_to_copy, tags=tags, env=env,
                                      exclude=exclude, git_info=git_info, random_name=random_name,
                                      with_mpi=with_mpi))

    return experiments


def get_container_types():
    ret = [list, tuple]
    try:
        import numpy as np
        ret.append(np.ndarray)
    except ImportError:
        pass
    try:
        import pandas as pd
        ret.append(pd.Series)
    except ImportError:
        pass
    return tuple(ret)


# TODO(pm): refactor me please
def get_combinations(param_grids, limit=None):
    """
    Based on sklearn code for grid search. Get all hparams combinations based on
    grid(s).
    :param param_grids: dict representing hparams grid, or list of such
    mappings
    :returns: list of OrderedDict (if params_grids consisted OrderedDicts,
     the Order of parameters will be sustained.)
    """
    allowed_container_types = get_container_types()
    if isinstance(param_grids, Mapping):
        # Wrap dictionary in a singleton list to support either dict or list of
        # dicts.
        param_grids = [param_grids]

    combinations = []
    for param_grid in param_grids:
        items = param_grid.items()
        if not items:
            combinations.append(OrderedDict())
        else:
            keys___ = []
            grids___ = []
            keys = []
            grids = []

            for key, grid in items:
                if '___' in key:
                    keys___.append(key[:-3])
                    grids___.append(grid)
                else:
                    keys.append(key)
                    grids.append(grid)

            for grid in grids + grids___:
                assert isinstance(grid, allowed_container_types), \
                    'grid values should be passed in one of given types: {}, got {} ({})' \
                    .format(allowed_container_types, type(grid), grid)

            if grids___:
                for param_values___ in zip(*grids___):
                    for param_values in product(*grids):
                        combination = OrderedDict(zip(keys___ + keys, param_values___ + param_values))
                        combinations.append(combination)
            else:
                for param_values in product(*grids):
                    combination = OrderedDict(zip(keys, param_values))
                    combinations.append(combination)

    if limit:
        combinations = combinations[:limit]
    return combinations
