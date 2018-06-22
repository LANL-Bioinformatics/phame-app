from django.urls import path

from . import views

app_name = "phame_app"
urlpatterns = [
    path("", view=views.index, name="index"),
    ]
