import logging
import os

import mrunner.settings

try:
    import neptune
except ImportError:
    print("pip install neptune-client to use restore-helper")

log = logging.getLogger(__name__)


class NeptuneHelper(object):
    def __init__(self, organization, project_name, api_token=None):
        self.api_token = api_token
        if api_token is None:
            self.api_token = self.get_api_token()

        self.session = neptune.Session(api_token=self.api_token)
        self.organization = organization
        self.project_name = organization + "/" + project_name

        self.projects = self.session.get_projects(self.organization)
        self.project = self.projects[self.project_name]

    @staticmethod
    def get_api_token():
        if "NEPTUNE_API_TOKEN" in os.environ:
            return os.environ["NEPTUNE_API_TOKEN"]
        elif "NEPTUNE_API_TOKEN_" in os.environ:
            return os.environ["NEPTUNE_API_TOKEN_"]
        else:
            log.error("NEPTUNE_API_TOKEN not found")
            exit(-1)

    def get_experiments(self, id=None, tag=None):
        return self.project.get_experiments(id=id, tag=tag)


def restore_helper(
    organization, project, id=None, tag=None, copy_mask="*", send_code=None
):
    assert (
        not mrunner.settings.NEPTUNE_USE_NEW_API,
        "Restore helper not yet supported with new neptune API!",
    )

    if send_code is None:
        send_code = copy_mask != "*"
    print("send_code", send_code)

    helper = NeptuneHelper(organization, project)
    experiments = helper.get_experiments(id=id, tag=tag)

    path_list = [e.get_properties()["pwd"] + "/" + copy_mask for e in experiments]
    experiments_specs = [
        {"organization": organization, "project": project, "id": e.id}
        for e in experiments
    ]
    return {
        "restore_from_path___": path_list,
        "neptune_parent_experiment_spec___": experiments_specs,
        "send_code___": [send_code] * len(experiments_specs),
    }
