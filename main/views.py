from django.shortcuts import render

def index(request):
    """Professional landing page"""
    return render(request, 'main/landing.html')
