from celery import shared_task
from .services import get_diff_from_github
from pprint import pprint

@shared_task
def review_pr(context):
    diff_data = get_diff_from_github(context['diff_url'], context['installation_id'])
    pprint(diff_data)