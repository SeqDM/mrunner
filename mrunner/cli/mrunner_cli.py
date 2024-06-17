#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import tempfile
import traceback
from pprint import pformat

import click
from path import Path

from mrunner.backends import get_backend
from mrunner.cli.config import ConfigParser
from mrunner.cli.config import context as context_cli
from mrunner.experiment import generate_experiments
from mrunner.utils.utils import WrapperCmd, validate_context

LOGGER = logging.getLogger(__name__)


def get_default_config_path(ctx):
    default_config_file_name = "config.yaml"

    app_name = Path(ctx.command_path).stem
    app_dir = Path(click.get_app_dir(app_name))
    return app_dir / default_config_file_name


after_run_callbacks = []


def register_after_run_callback(callback):
    """Registers a callback to be called after each invocation of `run`.

    For now only supports the SLURM backend.

    Args:
        callback: Function (backends.slurm.ExperimentRunOnSlurm, [experiment.Experiment]) -> None.
    """
    after_run_callbacks.append(callback)


def _get_contexts(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> list[str]:
    """Auto complete for option "context" based on contexts in config file.

    :param ctx: The current command context.
    :param args: The current parameter requesting completion.
    :param incomplete: The partial word that is being completed, as a
        string. May be an empty string '' if no characters have
        been entered yet.
    :return: List of possible contexts read from a config file

    TODO: Add some tests based on
    https://stackoverflow.com/questions/58577801/python-click-autocomplete-for-str-str-option
    """

    if "config" not in ctx.params:
        return []

    config_path = ctx.params["config"]

    config = ConfigParser(Path(config_path)).load()

    opts = config.contexts
    return [arg for arg in opts if arg.startswith(incomplete)]


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    default=0,
    help="Change verbosity level 0-warning, 1-info, 2-debug",
)
@click.option(
    "--config",
    default=None,
    type=click.Path(dir_okay=False),
    help="Path to mrunner yaml configuration",
)
@click.option("--cpu", default=None, type=int, help="Number of cpus to use")
@click.option("--nodes", default=None, type=int, help="Number of nodes to use")
@click.option("--mem", default=None, type=str, help="Amount of memory. E.g. 5G")
@click.option("--time", default=None, type=int, help="Time in minutes")
@click.option("--cmd_type", default=None, type=str, help="srun/sbatch")
@click.option("--partition", default=None, type=str, help="partition to use")
@click.option("--ntasks", default=None, type=str, help="ntasks")
@click.option(
    "--context",
    type=str,
    default=None,
    help="Name of remote context to use "
    '(if not provided, "contexts.current" conf key will be used)',
    shell_complete=_get_contexts,
)
@click.pass_context
def cli(ctx, verbose, config, context, **kwargs):
    """Deploy experiments on computation cluster"""

    modules_to_suppress_logging = [
        "pykwalify",
        "docker",
        "kubernetes",
        "paramiko",
        "requests.packages",
    ]
    verbosity = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}[min(verbose, 2)]
    logging.basicConfig(level=verbosity)
    for module in modules_to_suppress_logging:
        logging.getLogger(module).setLevel(logging.ERROR)

    # read configuration
    config_path = Path(config or get_default_config_path(ctx))
    LOGGER.debug("Using {} as mrunner config".format(config_path))
    config = ConfigParser(config_path).load()

    cmd_require_context = ctx.invoked_subcommand not in ["context"]
    if cmd_require_context:
        context_name = context or config.current_context or None
        if not context_name:
            raise click.ClickException(
                'Provide context name (use CLI "--context" option or use "mrunner context set-active" command)'
            )
        if context_name not in config.contexts:
            raise click.ClickException(
                f"Could not find predefined context: {context_name}. Use context add command."
            )

        try:
            context = config.contexts[context_name]
            res = {k: v for k, v in kwargs.items() if v is not None}
            context.update(res)
            LOGGER.info("Config to be used:")
            LOGGER.info("\n %s", pformat(context))

            context["context_name"] = context_name
            validate_context(context)

        except KeyError as exc:
            raise click.ClickException(f"Unknown context {context_name}") from exc
        except AttributeError as e:
            raise click.ClickException(e)

    ctx.obj = {"config_path": config_path, "config": config, "context": context}


@cli.command()
@click.option(
    "--spec",
    default="experiments_list",
    help="Name of function providing experiment specification",
)
@click.argument(
    "script",
    type=click.Path(dir_okay=False),
)
@click.argument("params", nargs=-1)
@click.pass_context
def run(ctx, spec, script, params):
    """Run experiment"""

    context = ctx.obj["context"]

    tmp_dir = tempfile.TemporaryDirectory()
    dump_dir = Path(tmp_dir.name)
    experiments = []

    for config_path, experiment in generate_experiments(
        script, context, spec=spec, dump_dir=dump_dir
    ):
        # TODO(mo): Can cmd be created and passed any other way?
        cmd = " ".join([experiment["script"]] + list(params))
        experiment["cmd"] = WrapperCmd(cmd=cmd, experiment_config_path=config_path)

        experiments.append(experiment)

    num_of_retries = 5
    ok = None
    result = None
    for _ in range(num_of_retries):
        try:
            result = get_backend(experiment["backend_type"]).run(
                experiments=experiments
            )
            ok = True
            break
        except Exception as e:
            LOGGER.error(
                "Caught exception: %s. Retrying until %d times.\n%s",
                str(e),
                num_of_retries,
                traceback.format_exc(),
            )
            ok = False
    if not ok:
        raise RuntimeError(f"Failed for {num_of_retries} times. Give up.")

    # Call the registered callbacks.
    if result is not None:
        (sweep, experiments) = result
        for callback in after_run_callbacks:
            callback(sweep, experiments)


cli.add_command(context_cli)

if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    cli()
