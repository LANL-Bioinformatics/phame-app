import subprocess
import os

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic.edit import FormView
from django.views import View
from django.template.loader import render_to_string
from django.conf import settings

from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response

from phame_api01.phame_app.forms import PhameInputForm
from phame_api01.phame_app.models import Run
from phame_api01.phame_app.serializers import RunSerializer

def input(request):
    if request.method == 'POST':
        form = PhameInputForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['data'] in [1, 2, 5] and form.cleaned_data['reference'] != 2:
                return render(request, 'phame_app/input.html', {'form': form})
            Run.objects.create(**form.cleaned_data)
            return HttpResponseRedirect('/input/')

    else:
        form = PhameInputForm()

    return render(request, 'phame_app/input.html', {'form': form})

class InputView(FormView):
    form_class = PhameInputForm
    template_name = 'phame_app/input.html'
    success_url = '/phame_app/run'

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        ref_dir = request.FILES.getlist('ref_dir')
        work_dir = request.FILES.getlist('work_dir')
        if form.is_valid():
            # if form.cleaned_data['data'] in [1, 2, 5] and form.cleaned_data['reference'] != 2:
            #     return render(request, 'phame_app/input.html', {'form': form})
            # Run.objects.create(**form.cleaned_data)
            return self.form_valid(form)

class RunView(View):
    renderer_classes = (TemplateHTMLRenderer, )
    def get(self, request):
        # run_objs = Run.objects.filter(edge_proj_name=request.data['edge-proj-name'])
        # run_values = run_objs.values()[0]
        # user_proj = UsersProjects.objects.get(run=run_values['id'])
        # run_serializer = RunSerializer(data=run_values)
        #

        all_runs = Run.objects.filter(id=1)
        run = all_runs.values()[0]
        run_serializer = RunSerializer(data=run)
        run_serializer.is_valid()
        run_dict = dict(run_serializer.data)
        content = render_to_string('phame_app/phame.tmpl', run_dict)
        # output_dir = os.path.join(settings.MEDIA_ROOT, 'edge_ui/EDGE_output', user_proj.user_path)
        # if not os.path.exists(output_dir):
        #     os.mkdir(output_dir)
        config_file_path = os.path.join(settings.MEDIA_ROOT, 'config.ctl')
        with open(config_file_path, 'w') as config_file:
            config_file.write(content)
        p1 = subprocess.Popen('docker run --rm -v $/Devel/phame_examples/ecoli:/data phame_api01_phame-1 perl src/runPhaME.pl /data/ecoli.ctl',
                              shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p1.communicate()
        return Response(content)
