from django.forms import ModelForm
from django import forms
from phame_api01.phame_app.models import Run

class PhameInputForm(ModelForm):
    class Meta:
        model = Run
        fields = ['ref_dir', 'work_dir', 'reference', 'ref_file', 'project', 'cds_snps', 'buildSNPdb', 'first_time', 'data',
                  'reads', 'tree', 'bootstrap', 'N', 'pos_select', 'code', 'clean', 'cutoff', 'threads']

    ref_dir = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple':True, 'webkitdirectory': True, 'directory': True}), required=False)
    work_dir = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple':True, 'webkitdirectory': True, 'directory': True}), required=False)
    ref_file = forms.FileField(label='reference file', required=False)
    reference = forms.ChoiceField(widget=forms.Select(), choices=Run.REF_CHOICES, initial='1', required=False)
    project = forms.CharField(initial='ecoli', label='main alignment file name', required=False)
    cds_snps = forms.ChoiceField(widget=forms.Select(), choices=Run.BOOL_CHOICES, initial='1', required=False)
    buildSNPdb = forms.ChoiceField(widget=forms.Select(), choices=Run.BOOL_CHOICES, initial='1', required=False)
    first_time = forms.ChoiceField(widget=forms.Select(), choices=Run.BOOL_CHOICES, initial='1', required=False)

    data = forms.ChoiceField(widget=forms.Select(), choices=Run.DATA_CHOICES, initial='1', required=False)
    reads = forms.ChoiceField(widget=forms.Select(),choices=Run.READS_CHOICES, initial='1', required=False)
    tree = forms.ChoiceField(widget=forms.Select(), choices=Run.TREE_CHOICES, initial='1', required=False)
    bootstrap = forms.ChoiceField(widget=forms.Select(), choices=Run.BOOL_CHOICES, initial='1', required=False)
    N = forms.IntegerField(initial=100, required=False)

    pos_select = forms.ChoiceField(widget=forms.Select(), choices=Run.POS_CHOICES, initial='1', required=False)
    code = forms.ChoiceField(widget=forms.Select(), choices=Run.CODE_CHOICES, initial='1', required=False)
    clean = forms.ChoiceField(widget=forms.Select(), choices=Run.BOOL_CHOICES, initial='1', required=False)
    threads = forms.IntegerField(initial=2, required=False)
    cutoff = forms.FloatField(initial=0.1, required=False)
