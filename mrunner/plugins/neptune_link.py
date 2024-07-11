"""Provides `print_neptune_link` plugin - prints a link to the future neptune experiment.

Put
print_neptune_link as a callback in create_experiments_helper

experiments_list = create_experiments_helper(
        base_config={}

        params_grid={},
        script="..",
        ....
        callback=[print_neptune_link],
    )
"""


def _get_neptune_link(project_name, random_name, add_random_tag, html_link=False, **other_kwargs):
    assert add_random_tag, "This plugin works properly only if" \
                           " random tag is added to the experiment. That is add_random_tag=True"

    organization, project_name = project_name.split("/")
    neptune_link = rf"https://app.neptune.ai/o/{organization}/org/{project_name}/runs/details?viewId=standard-view&detailsTab=metadata&type=run&path=sys&attribute=tags&query=((%60sys%2Ftags%60%3AstringSet%20CONTAINS%20%22{random_name}%22))&sortBy=%5B%22sys%2Fcreation_time%22%5D&sortFieldType=%5B%22datetime%22%5D&sortFieldAggregationMode=%5B%22auto%22%5D&sortDirection=%5B%22descending%22%5D&suggestionsEnabled=true&lbViewUnpacked=true"
    if html_link:
        return rf'<a href="{neptune_link}"><b>{random_name}</b></a>'
    return neptune_link


def print_neptune_link(**kwargs):
    neptune_link = _get_neptune_link(**kwargs)
    print(rf"Neptune link to the future experiment is:{neptune_link}")

# print_neptune_link(project_name="pmtest/ProteinMultimodal", random_name="infallible_knuth", add_random_tag=True)
