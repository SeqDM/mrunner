"""Provides `print_neptune_link` plugin - prints a link to the future neptune experiment."""


def _get_neptune_link(project_name, random_tag_name):
    organization, project_name = project_name.split("/")
    return rf"https://app.neptune.ai/o/{organization}/org/{project_name}/runs/details?viewId=standard-view&detailsTab=metadata&shortId=EF-6833&type=run&path=sys&attribute=tags&query=((%60sys%2Ftags%60%3AstringSet%20CONTAINS%20%22{random_tag_name}%22))&sortBy=%5B%22sys%2Fcreation_time%22%5D&sortFieldType=%5B%22datetime%22%5D&sortFieldAggregationMode=%5B%22auto%22%5D&sortDirection=%5B%22descending%22%5D&suggestionsEnabled=true&lbViewUnpacked=true"


def print_neptune_link(project_name, random_name, **other_kwargs):
    neptune_link = _get_neptune_link(project_name, random_name)
    print(rf"Neptune link to the future experiment is:{neptune_link}")
