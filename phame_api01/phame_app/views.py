import subprocess
import os
import requests

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic.edit import FormView
from django.views import View
from django.template.loader import render_to_string
from django.conf import settings

from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response

from phame_api01.phame_app.forms import PhameInputForm
from phame_api01.phame_app.models import Run, ReferenceFile, WorkFile
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
            f = form.save(commit=False)
            f.work_dir = '../media/workdir'
            f.ref_dir = '../media/refdir'
            f.save()
            if len(ref_dir) > 0:
                run = Run.objects.filter().order_by('-id')[0]
                for ref_file in ref_dir:
                    instance = ReferenceFile(run=run, ref_file=ref_file)
                    instance.save()
            if len(work_dir) > 0:
                run = Run.objects.filter().order_by('-id')[0]
                for work_file in work_dir:
                    instance = WorkFile(run=run, work_file=work_file)
                    instance.save()
            return self.form_valid(form)

class RunView(View):
    renderer_classes = (TemplateHTMLRenderer, )
    def get(self, request):
        run = Run.objects.filter().order_by('-id').values()[0]
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
        # p1 = subprocess.Popen('docker run --rm -v /Devel/phame_examples/ecoli:/data phame_api01_phame-1 perl src/runPhaME.pl /data/ecoli.ctl',
        #                       shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # p1.communicate()
        r = requests.get('http://phame:5000/run')
        return HttpResponseRedirect('/phame_app/input')
