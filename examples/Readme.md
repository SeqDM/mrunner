An mrunner kickstart pack:

Get the following values from up.neptune.ml. Click help and then quickstart.

```
export NEPTUNE_API_TOKEN = ...
export PROJECT_QUALIFIED_NAME = ...
```
Run basic setup
```
basic_setup.sh <your plgrid login> <grant which you have access to>
```
For example
```
basic_setup.sh plgloss planningrl
```

Run experiments
```
run_examples.sh
```

To run on GCP create and download Service Account Key
https://cloud.google.com/docs/authentication/production
```
export GOOGLE_APPLICATION_CREDENTIALS = /path/to/key.json

```

To test if works try
```
mrunner --config resources/prometheus_config_template.yaml --context test_kube run experiment_gcp_conf.py --base_image loss/gfootball --requirements_file resources/requirements.txt
```
