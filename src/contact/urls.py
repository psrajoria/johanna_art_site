from django.urls import path

from . import views

app_name = "contact"

urlpatterns = [
    path("inquiry/", views.inquiry_create, name="inquiry"),
    path("thanks/<str:token>/", views.thanks, name="thanks"),
    path("request/<str:token>/", views.request_status, name="request_status"),
    path("reference/<int:pk>/", views.reference_image, name="reference"),
]
