import subprocess
import os
import requests
import shutil
import pandas as pd

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic.edit import FormView
from django.views import View
from django.template.loader import render_to_string
from django.template import loader
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
            if len(ref_dir) > 0:
                self.remove_input_files(settings.MEDIA_ROOT)
                self.insert_files(ref_dir, 'ref_dir')

            if len(work_dir) > 0:
                self.remove_input_files(settings.MEDIA_ROOT)
                self.insert_files(work_dir, 'work_dir')

            return self.form_valid(form)

    @staticmethod
    def remove_input_files(dir):
        if len(os.listdir(dir)) > 0:
            for root, dirs, files in os.walk(dir):
                for dir in dirs:
                    shutil.rmtree(os.path.join(root, dir))
                for file in files:
                    os.remove(os.path.join(root, file))

    @staticmethod
    def insert_files(dir_files, dir_name):
        run = Run.objects.filter().order_by('-id')[0]
        if dir_name == 'ref_dir':
            for ref_file in dir_files:
                instance = ReferenceFile(run=run, ref_file=ref_file)
                instance.save()
        else:
            for work_file in dir_files:
                instance = WorkFile(run=run, work_file=work_file)
                instance.save()


class RunView(View):
    renderer_classes = (TemplateHTMLRenderer, )
    def get(self, request):
        run = Run.objects.filter().order_by('id').values()[3]
        run_serializer = RunSerializer(data=run)
        run_serializer.is_valid()
        run_dict = dict(run_serializer.data)
        run_dict['work_dir'] = '../media/workdir'
        run_dict['ref_dir'] = '../media/refdir'
        content = render_to_string('phame_app/phame.tmpl', run_dict)
        config_file_path = os.path.join(settings.MEDIA_ROOT, 'config.ctl')
        with open(config_file_path, 'w') as config_file:
            config_file.write(content)
        # p1 = subprocess.Popen('docker run --rm -v /Devel/phame_examples/ecoli:/data phame_api01_phame-1 perl src/runPhaME.pl /data/ecoli.ctl',
        #                       shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # p1.communicate()
        r = requests.get('http://phame:5000/run')
        print(r.content)
        template = loader.get_template('phame_app/output.html')

        coords = []
        with open(os.path.join(settings.MEDIA_ROOT, 'workdir', 'results', 'CDScoords.txt'), 'r') as fp:
            lines = fp.readlines()
            for line in lines:
                line_split = line.split()
                coords.append({'name':line_split[0], 'coord1':line_split[1], 'coord2':line_split[2],
                               'type':line_split[3]})

        comps = []
        with open(os.path.join(settings.MEDIA_ROOT, 'workdir', 'results',
                               '{0}_summaryStatistics.txt'.format(run_dict['project'])), 'r') as fp:
            lines = fp.readlines()
            for line in lines:
                comps.append({'line':line})

        ref_files = ReferenceFile.objects.filter(run_id=run['id'])
        comparisons_table = pd.read_table(os.path.join(settings.MEDIA_ROOT, 'workdir', 'results',
                                                       '{0}_comparisons.txt'.format(run_dict['project'])),
                                          header=1, index_col=0)
        comps_cols = comparisons_table.columns[1:]
        comps = comparisons_table.loc[:, comps_cols].to_dict()

        return HttpResponse(template.render({'run_phame_output': str(r.content), 'coords':coords, 'comps':comps}, request))
