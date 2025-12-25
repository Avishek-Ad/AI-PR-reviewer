from celery import shared_task
from .services import get_diff_from_github, chunk_hunks, final_verification, post_review_to_github
from .schemas import ReviewResponse
from unidiff import PatchSet
from pprint import pprint
from groq import Groq
from openai import OpenAI
import instructor
import os
from dotenv import load_dotenv
load_dotenv()

system_prompt = """You are a senior code reviewer. You will be provided with code snippets labeled with their absolute line numbers.
Instructions:
Only suggest improvements for lines starting with "Line X: +".
If you find an issue, your response must be a JSON array.
Use the exact "Line X" number provided in the input for your line_number field.
Input: File: app.py {hunk_for_llm}
"""

client = instructor.from_openai(
    OpenAI(
        api_key=os.environ.get('GROQ_API_KEY'),
        base_url="https://api.groq.com/openai/v1",
    )
)

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
        # print("".join(chunk))

        # send it to llm and store each result in responses
        try:
            llm_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile", # One of their best free models
                response_model=ReviewResponse,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "".join(chunk)}
                ],
            )
            responses.append(llm_response)
        except Exception as e:
            print("ERROR: ", str(e))

    # do some processing on the
    reviews = final_verification(patch, responses)
    # pprint(reviews)

    # post the comments to github as review
    response_gh = post_review_to_github(context, reviews)
    # print(response_gh)