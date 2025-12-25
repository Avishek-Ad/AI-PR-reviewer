from celery import shared_task
from .services import get_diff_from_github, chunk_hunks
from unidiff import PatchSet
from pprint import pprint

@shared_task
def review_pr(context):
    diff_data = get_diff_from_github(context['diff_url'], context['installation_id'])
    patch = PatchSet(diff_data)
    responses = []
    chunk_data = chunk_hunks(patch)

    while True:
        chunk = next(chunk_data, None)
        if not chunk:
            break
        print("".join(chunk))

        # send it to llm and store each result in responses

    # do some processing on the responses

    # post the comments to github as review