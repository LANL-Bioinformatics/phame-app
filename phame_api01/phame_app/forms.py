from django.forms import ModelForm
from django import forms
from phame_api01.phame_app.models import Run

class PhameInputForm(forms.Form):

    ref_dir = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple':True, 'webkitdirectory': True, 'directory': True}), required=False)
    work_dir = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple':True, 'webkitdirectory': True, 'directory': True}), required=False)
    ref_file = forms.FileField(label='reference file', required=False)
    reference = forms.ChoiceField(widget=forms.Select(), choices=Run.REF_CHOICES, initial='1', required=False)
    project = forms.CharField(initial='ecoli', label='main alignment file name', required=False)
    cds_snps = forms.ChoiceField(widget=forms.Select(), choices=Run.CDS_CHOICES, initial='1', required=False)
    buildSNPdb = forms.ChoiceField(widget=forms.Select(), choices=Run.BUILD_CHOICES, initial='1', required=False)
    first_time = forms.ChoiceField(widget=forms.Select(), choices=Run.FIRST_CHOICES, initial='1', required=False)

    data = forms.ChoiceField(widget=forms.Select(), choices=Run.DATA_CHOICES, initial='0')
    reads = forms.ChoiceField(widget=forms.Select(),choices=Run.READS_CHOICES, initial='2')
    aligner = forms.ChoiceField(widget=forms.Select(), choices=Run.ALIGNER_CHOICES, initial=Run.ALIGNER_CHOICES[0])
    tree = forms.ChoiceField(widget=forms.Select(), choices=Run.TREE_CHOICES, initial='1')
    bootstrap = forms.ChoiceField(widget=forms.Select(), choices=Run.BOOL_CHOICES, initial='1')
    N = forms.IntegerField(initial=100, required=False)

    pos_select = forms.ChoiceField(widget=forms.Select(), choices=Run.POS_CHOICES, initial='1')
    code = forms.ChoiceField(widget=forms.Select(), choices=Run.CODE_CHOICES, initial='1')
    clean = forms.ChoiceField(widget=forms.Select(), choices=Run.BOOL_CHOICES, initial='1')
    threads = forms.IntegerField(initial=2)
    cutoff = forms.FloatField(initial=0.1)
