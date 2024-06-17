# Changelog

All notable changes to this project will be documented in this file.

Descritions are grouped by the type of change: added, changed, deprecated, removed, fixed, security.

## [Unreleased]

### Added
* Documentation.
* Auto completion of `--context` parameter based on contexts in the config file.
* Missing and additional keys reporting for contexts in config file.
* Extended README.md.

### Changed
* `mrunner run` no longer accepts `base_image` and `requirements_file` as parameters - from now on the Kubernetes backend context should supply those.
* Refactored atribute classes for both backends.

### Removed
* Removed support for `neptune<1.0.0`.
* Temporarily removed `mrunner.helpers.restore_helper`.

### Fixed
* Experiment name is adjusted to work on clusters.

## 23.04
### Added
* `--verbosity` parameter to `mrunner`.
* Plugins functionality (`mrunner.plugins` package).
* Improved error logs in `mrunner run`.

## Fixed
* Removed arbitrary default constants and unnecessary assertion in `mrunner.backends.slurm`.
