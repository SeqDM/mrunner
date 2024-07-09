# -*- coding: utf-8 -*-
import logging
import tarfile
import tempfile

import attr
from attrs import Factory, define, field
from fabric import Connection
from path import Path

from mrunner.experiment import ContextBase, Experiment
from mrunner.utils.namesgenerator import id_generator
from mrunner.utils.utils import (
    GeneratedTemplateFile,
    filter_only_attr,
    get_paths_to_copy,
    pathify,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_SCRATCH_DIR = "mrunner_scratch"
DEFAULT_CACHE_DIR = ".cache"
DEFAULT_LOGS_DIR_NAME = "logs"
DEFAULT_CONFIGS_DIR_NAME = "configs"
TMP_CONFIGS_DIR = "___configs___"  # temporary directory name to send configs using the same zip as code, it should be very unique


@define(kw_only=True)
class SlurmContext(ContextBase):
    slurm_url: str
    partition: str = None
    account: str = None
    log_output_path: str = None
    time: str = "30"
    ntasks: str = "1"
    cpu: str = "0"
    gpu: str = "0"
    mem: str = "5GB"
    nodes: str = "1"
    qos: str = None
    nodelist: str = None
    exclude_nodes: str = None
    modules_to_load: list[str] = Factory(list)
    sbatch_options: list[str] = Factory(list)
    prolog_cmd: str = ""
    cmd_type: str = "srun"
    requirements_file: str = None
    venv: str = None
    conda: str = None
    singularity_container: str = None
    scratch_dir_name: str = DEFAULT_SCRATCH_DIR
    cache_dir_name: Path = DEFAULT_CACHE_DIR
    grid_logs_dir_name: str = DEFAULT_LOGS_DIR_NAME
    grid_configs_dir_name: str = DEFAULT_CONFIGS_DIR_NAME


@define
class _SlurmExperiment(SlurmContext, Experiment):
    _experiment_scratch_dir: Path = field(init=False, default=None)

    @property
    def scratch_dir(self):
        return Path(self.storage_dir) / pathify(self.scratch_dir_name)

    @property
    def cache_dir(self):
        return self.scratch_dir / pathify(self.cache_dir_name)

    @property
    def project_scratch_dir(self):
        return self.scratch_dir / pathify(self.project.split("/")[-1])

    @property
    def grid_scratch_dir(self):
        return self.project_scratch_dir / pathify(self.unique_name)

    @property
    def experiment_scratch_dir(self):
        if self._experiment_scratch_dir is None:
            # TODO(pj): Change id_generator to hyper-params shorthand
            self._experiment_scratch_dir = self.grid_scratch_dir / pathify(
                self.name + "_" + id_generator(4)
            )
        return self._experiment_scratch_dir

    @property
    def grid_logs_dir(self):
        return self.grid_scratch_dir / self.grid_logs_dir_name

    @property
    def grid_configs_dir(self):
        return self.grid_scratch_dir / self.grid_configs_dir_name


class ExperimentScript(GeneratedTemplateFile):
    DEFAULT_SLURM_EXPERIMENT_SCRIPT_TEMPLATE = "slurm_experiment.sh.jinja2"

    def __init__(self, experiment: _SlurmExperiment):
        super(ExperimentScript, self).__init__(
            template_filename=self.DEFAULT_SLURM_EXPERIMENT_SCRIPT_TEMPLATE,
            experiment=experiment,
        )
        self.experiment = experiment
        self.path.chmod("a+x")

    @property
    def script_name(self):
        e = self.experiment
        return "{}.sh".format(e.experiment_scratch_dir.relpath(e.project_scratch_dir))


class SlurmWrappersCmd(object):

    def __init__(self, experiment, script_path, array_size, cmd_type):
        self._experiment = experiment
        self._script_path = script_path
        self.array_str = rf"0-{array_size-1}"
        self._cmd = cmd_type

    @property
    def command(self):
        # see: https://slurm.schedmd.com/srun.html
        # see: https://slurm.schedmd.com/sbatch.html
        cmd_items = [self._cmd]

        def _extend_cmd_items(cmd_items, option, data_key, default=None):
            value = self._getattr(data_key)
            if value:
                cmd_items += [option, str(value)]
            elif default:
                cmd_items += [option, default]

        default_log_path = (
            self._experiment.grid_logs_dir / "slurm_%a.log"
            if self._cmd == "sbatch"
            else None
        )
        _extend_cmd_items(cmd_items, "-A", "account")
        _extend_cmd_items(
            cmd_items, "-o", "log_output_path", default_log_path
        )  # output
        _extend_cmd_items(cmd_items, "-p", "partition")
        _extend_cmd_items(cmd_items, "-t", "time")
        _extend_cmd_items(cmd_items, "--qos", "qos")
        _extend_cmd_items(cmd_items, "--nodelist", "nodelist")
        _extend_cmd_items(cmd_items, "--exclude", "exclude_nodes")
        _extend_cmd_items(cmd_items, "--array", "array_str")

        cmd_items += self._resources_items()
        cmd_items += [self._script_path]

        return " ".join(cmd_items)

    def _getattr(self, key):
        return getattr(self, key, getattr(self._experiment, key, None))

    def _resources_items(self):
        """mapping from mrunner notation into slurm"""
        cmd_items = []
        # mrunner_resources = self._getattr('resources')
        # TODO(pm): Refactor me please
        mrunner_resources = {}
        for resource_type in ["cpu", "gpu", "mem", "nodes"]:
            if self._getattr(resource_type):
                mrunner_resources[resource_type] = self._getattr(resource_type)
        for resource_type, resource_qty in mrunner_resources.items():
            if resource_type == "cpu":
                ntasks = int(self._getattr("ntasks") or 1)
                cores_per_task = int(int(resource_qty) / ntasks)
                cmd_items += ["-c", str(cores_per_task)]

                if ntasks > 1:
                    cmd_items += ["-n", str(ntasks)]
                    LOGGER.debug("Running %d tasks", ntasks)
                total_cpus = cores_per_task * ntasks
                if total_cpus != int(resource_qty):
                    LOGGER.warning(
                        "Will request %d CPU instead of %d",
                        total_cpus,
                        int(resource_qty),
                    )
                LOGGER.debug(
                    "Using %d/%d CPU cores per_task/total", cores_per_task, total_cpus
                )
            elif resource_type == "gpu":  # TODO(PM): does not work at the moment
                cmd_items += ["--gres", f"gpu:{int(resource_qty)}"]
                LOGGER.debug("Using %d gpu", int(resource_qty))
            elif resource_type == "mem":
                cmd_items += ["--mem", str(resource_qty)]
                LOGGER.debug("Using %s memory", resource_qty)
            elif resource_type == "nodes":
                cmd_items += ["--nodes", str(resource_qty)]
            else:
                raise ValueError(
                    f"Unsupported resource request: {resource_type}={resource_qty}"
                )

        return cmd_items


@attr.s
class SlurmBackend(object):

    initialized = attr.ib(default=False, init=False)
    conn_cache = {}

    def run(self, experiments):

        experiment = experiments[
            0
        ]  # Assume that all experiments share deployment config. This should be reflected in all code.
        # configure fabric
        slurm_url = experiment["slurm_url"]
        if slurm_url in self.conn_cache:
            self.connection = self.conn_cache[slurm_url]
            LOGGER.debug("REUSING cached connection")
        else:
            LOGGER.debug("NEW connection connection")
            self.connection = Connection(slurm_url)
            self.conn_cache[slurm_url] = self.connection

        # create Slurm experiment
        experiment = _SlurmExperiment(
            **filter_only_attr(_SlurmExperiment, experiment),
        )

        # create experiment script
        script = ExperimentScript(experiment)
        remote_script_path = experiment.project_scratch_dir / script.script_name
        archive_remote_path = experiment.cache_dir / experiment.unique_name

        LOGGER.debug("Configuration: {}".format(experiment))

        self.ensure_directories(experiment)
        self.cache_code(experiment, archive_remote_path)
        self.deploy_code(experiment, archive_remote_path)
        self.send_script(script, remote_script_path)

        cmd = SlurmWrappersCmd(
            experiment=experiment,
            script_path=remote_script_path,
            array_size=len(experiments),
            cmd_type=experiment.cmd_type,
        )
        self._fabric_run(cmd.command, warn=False)
        return (experiment, experiments)

    def ensure_directories(self, experiment):
        self._ensure_dir(experiment.experiment_scratch_dir)
        self._ensure_dir(experiment.grid_logs_dir)
        if not self.initialized:
            self._ensure_dir(experiment.cache_dir)
            self.initialized = True

    def cache_code(self, experiment, archive_remote_path):
        if not experiment.send_code:
            return
        if self._file_exists(archive_remote_path):
            return

        paths_to_copy = (
            experiment.paths_to_copy if experiment.paths_to_copy is not None else []
        )
        paths_to_copy.append(
            rf"{experiment.cmd._experiment_config_path.dirname()}:{TMP_CONFIGS_DIR}"
        )
        paths_to_dump = get_paths_to_copy(
            exclude=experiment.exclude, paths_to_copy=paths_to_copy
        )
        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as temp_file:
            # archive all files
            with tarfile.open(temp_file.name, "w:gz") as tar_file:
                for p in paths_to_dump:
                    LOGGER.debug(
                        'Adding "%s" to deployment archive', str(p.rel_remote_path)
                    )
                    try:
                        tar_file.add(p.local_path, arcname=p.rel_remote_path)
                    except PermissionError:
                        LOGGER.warning("Skipping %s: no access", str(p.local_path))

            # upload archive to cluster and extract
            self._put(temp_file.name, archive_remote_path)

    def deploy_code(self, experiment, archive_remote_path):
        if not experiment.send_code:
            return
        cd = f"cd {experiment.experiment_scratch_dir} ;  "
        self._fabric_run(
            cd
            + "tar xvf {tar_filename} > /dev/null".format(
                tar_filename=archive_remote_path
            )
        )
        self._fabric_run(
            f"mv {experiment.experiment_scratch_dir}/{TMP_CONFIGS_DIR} {experiment.grid_configs_dir}"
        )

    def send_script(self, script, remote_script_path):
        self._put(script.path, remote_script_path)

    def _put(self, local_path, remote_path):
        LOGGER.info("SSH: put local file %s as remote %s", local_path, remote_path)
        self.connection.put(local_path, remote_path)

    def _ensure_dir(self, directory_path):
        self._fabric_run("mkdir -p {path}".format(path=directory_path))

    def _fabric_run(self, cmd, warn=False):
        LOGGER.info("SSH: running command '%s'", cmd)
        return self.connection.run(cmd, warn=warn)

    def _file_exists(self, fname):
        return self._fabric_run(f"stat {fname}", warn=True).ok


_slurm_backend = None


def get_slurm_backend():
    global _slurm_backend
    if _slurm_backend is None:
        _slurm_backend = SlurmBackend()
    return _slurm_backend
