from django.shortcuts import render
from django.http import HttpResponse
from . models import Registration
from django.shortcuts import render


def index(request):
    return HttpResponse(
        f'<h1>Сервис BeautyCity</h1>')
