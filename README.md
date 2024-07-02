# mrunner

mrunner(meta-runner) is a tool intended to run experiment code on various computation systems, without manual deployment and with significantly less configuration. Main features include:

- Prepare remote environment,
- Deploy code,
- Run experiments,
  - Use of scheduler like Slurm or Kubernetes on the remote,
  - It is also possible to run experiment locally.
- Monitor experiments using [neptune](https://neptune.ai/).

Currently [slurm](https://slurm.schedmd.com) and _(possibly)_
[kubernetes](http://kubernetes.io) clusters are supported.

## Install

Run `pip install .` in the repo root dir after cloning it.

### Install MRunner auto-completion
To enable full auto completion (e.g. of contexts from config file) in **Bash** please run:
```
_MRUNNER_COMPLETE=bash_source mrunner > ~/.mrunner-complete.bash
echo ". ~/.mrunner-complete.bash >> ~/.bashrc
```
then, restart terminal session to make it work.

Instuctions on how to support Zsh, Fish and other shells are available on [the click package website](https://click.palletsprojects.com/en/8.1.x/shell-completion/).

## How to use?

More details may be found in the [examples](./examples).

Assumptions:
* We support running experiments in batches, however current implementation assumes that each run from the batch has the same hardware requirements. This is reflected in the fact that all runs from a grid use single context.

## Contributing
Please use pre-commit when contibuting to the repository. Install the package with `[dev]` option. And run `pre-commit install` before commiting any code to the repository. The pre-commit package handles proper formatting using black and isort.

### Documentation
Documentation is available at [mrunner24.readthedocs.io](https://mrunner24.readthedocs.io/en/latest/)

To generate the documentation locally run:
```
pip install -e .[doc]
sphinx-build -M html docs/source/ docs/build/
```

### Why using attrs?
Implementation of dataclasses from standard python 3.10 library possibly fulfills all our requirements. However to stay more flexible and support older versions of python (3.8, 3.9) we stick to attrs library. The key feature on which we realy is inheritance of atribute classes.
