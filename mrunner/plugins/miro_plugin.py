"""This is a miro integration for mrunner.

Put include_into_miro(miro_api_key="...", miro_experiment_board_id="...") as a callback in create_experiments_helper

experiments_list = create_experiments_helper(
        base_config={}

        params_grid={},
        script="..",
        ....
        callback=[include_into_miro(miro_api_key="...", miro_experiment_board_id="...")],
    )
"""
import requests
import os

from mrunner.plugins.neptune_link import _get_neptune_link


def _include_into_miro(miro_api_key, miro_experiment_board_id, include_netpune_link=True, experiment_name="", **other_kwargs):
    content = experiment_name
    if include_netpune_link:
        neptune_link = _get_neptune_link(**other_kwargs, html_link=True)

        stupid_formatting = "&nbsp;" * 7
        content += rf'<br>{stupid_formatting}{neptune_link}'


    url = rf"https://api.miro.com/v2-experimental/boards/{miro_experiment_board_id}/mindmap_nodes"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": "Bearer " + miro_api_key
    }


    payload = {"data": {"nodeView": {"data": {
                    "type": "text",
                    "content": content
                }}}}

    response = requests.post(url, json=payload, headers=headers)
    if response.json()['type'] == 'error':
        print("Error in creating a node. Check if the board id is correct.")
        print(response.json())


def include_into_miro(miro_api_key=None, miro_experiment_board_id=None):
    # if absent try to get from environment variables
    if miro_api_key is None:
        miro_api_key = os.environ.get("MIRO_API_KEY", None)
    if miro_experiment_board_id is None:
        miro_experiment_board_id = os.environ.get("MIRO_EXPERIMENT_BOARD_ID", None)

    assert miro_api_key is not None, "Use https://developers.miro.com/docs/rest-api-build-your-first-hello-world-app?utm_source=your_apps to get a key for a new app. Or ask a friend."
    assert miro_experiment_board_id is not None, "Create a board in miro and get its id. E.g. for https://miro.com/app/board/uXjVKzlRQ_U=/ it is uXjVKzlRQ_U="

    return lambda **kwargs: _include_into_miro(miro_api_key, miro_experiment_board_id, **kwargs)


# fun = include_into_miro(miro_experiment_board_id="uXjVKzlRQ_U=")
#
# test_dict = {'project_name': 'pmtest/ProteinMultimodal',
#              'experiment_name': 'aaa kotki dwa',
#              'random_name': 'infallible_knuth',
#              'add_random_tag': True}
# fun(**test_dict)