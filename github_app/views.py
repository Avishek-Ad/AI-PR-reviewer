from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def github_webhook(request):
    print("PING")
    return HttpResponse("OK", status=200)
    