from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "phame_app"
urlpatterns = [
    # path("", view=views.index, name="index"),
    path("input", view=views.InputView.as_view(), name="input"),
    path("run", view=views.RunView.as_view(), name="run"),
    # path("run/", TemplateView.as_view(template_name="phame_app/phame.tmpl"), name="run")
    ]
