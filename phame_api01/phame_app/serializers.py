from rest_framework import serializers, fields
from rest_framework.authtoken.models import Token
from django.conf import settings
from hashlib import blake2b
from .models import *

class RunSerializer(serializers.ModelSerializer):
    class Meta:
        model = Run
        fields = ('ref_dir', 'work_dir', 'reference', 'ref_file', 'project', 'cds_snps', 'buildSNPdb', 'first_time', 'data',
                  'reads', 'tree', 'bootstrap', 'N', 'pos_select', 'code', 'clean', 'cutoff', 'threads')

