from django.urls import path

from . import views

app_name = "contact"

urlpatterns = [
    path("inquiry/", views.inquiry_create, name="inquiry"),
    path("thanks/", views.thanks, name="thanks"),
]
