#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import tempfile
import traceback
from pprint import pformat

import click
from path import Path

from mrunner.backends.k8s import get_kubernetes_backend
from mrunner.backends.slurm import get_slurm_backend
from mrunner.cli.config import ConfigParser
from mrunner.cli.config import context as context_cli
from mrunner.experiment import generate_experiments
from mrunner.utils.utils import WrapperCmd

LOGGER = logging.getLogger(__name__)


def get_backend(backend_type):
    if backend_type == "kubernetes":
        return get_kubernetes_backend()
    if backend_type == "slurm":
        return get_slurm_backend()
    else:
        raise KeyError("No backend type: {}".format(backend_type))


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


@click.group()
@click.option("--debug/--no-debug", default=False, help="Enable debug messages")
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
    default=None,
    help="Name of remote context to use "
    '(if not provided, "contexts.current" conf key will be used)',
)
@click.pass_context
def cli(ctx, debug, config, context, **kwargs):
    """Deploy experiments on computation cluster"""

    log_tags_to_suppress = [
        "pykwalify",
        "docker",
        "kubernetes",
        "paramiko",
        "requests.packages",
    ]
    logging.basicConfig(level=debug and logging.DEBUG or logging.INFO)
    for tag in log_tags_to_suppress:
        logging.getLogger(tag).setLevel(logging.ERROR)

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
                'Could not find predefined context: "{}". Use context add command.'.format(
                    context_name
                )
            )

        try:
            context = config.contexts[context_name]
            res = {k: v for k, v in kwargs.items() if v is not None}
            context.update(res)
            LOGGER.info("Config to be used:")
            LOGGER.info("\n" + pformat(context))

            LOGGER.info("")
            LOGGER.info(
                "You can change config from commandline. E.g. mrunner ... --cpu 5"
            )
            LOGGER.info("")
            context["context_name"] = (
                context_name  # TODO(pm): This is probably never used
            )
            for k in ["storage_dir", "backend_type"]:
                if k not in context:
                    raise AttributeError('Missing required "{}" context key'.format(k))
        except KeyError:
            raise click.ClickException("Unknown context {}".format(context_name))
        except AttributeError as e:
            raise click.ClickException(e)

    ctx.obj = {"config_path": config_path, "config": config, "context": context}


@cli.command()
@click.option(
    "--spec",
    default="experiments_list",
    help="Name of function providing experiment specification",
)
@click.option(
    "--requirements_file", type=click.Path(), help="Path to requirements file"
)
@click.option("--base_image", help="Base docker image used in experiment")
@click.argument("script")
@click.argument("params", nargs=-1)
@click.pass_context
def run(ctx, spec, requirements_file, base_image, script, params):
    """Run experiment"""

    context = ctx.obj["context"]

    # validate options and arguments
    requirements = (
        requirements_file
        and [req.strip() for req in Path(requirements_file).open("r")]
        or []
    )
    if context["backend_type"] == "kubernetes" and not base_image:
        raise click.ClickException("Provide docker base image")
    if context["backend_type"] == "kubernetes" and not requirements_file:
        raise click.ClickException("Provide requirements.txt file")

    tmp_dir = tempfile.TemporaryDirectory()
    dump_dir = Path(tmp_dir.name)
    experiments = []

    for config_path, experiment in generate_experiments(
        script, context, spec=spec, dump_dir=dump_dir
    ):
        experiment.update({"base_image": base_image, "requirements": requirements})

        cmd = " ".join([experiment.pop("script")] + list(params))
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
    cli()
