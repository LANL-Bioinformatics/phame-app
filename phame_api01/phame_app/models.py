from django.db import models

# Create your models here.
class Run(models.Model):
    ref_dir = models.FileField(null=True)
    work_dir = models.FileField(null=True)

    REF_CHOICES = (('0', 'random'), ('1', 'given'), ('2', 'ANI'))
    reference = models.CharField(max_length=6, choices=REF_CHOICES)

    ref_file = models.FileField(null=True)
    project = models.CharField(max_length=20, default='ecoli')
    cds_snps = models.BooleanField(default=False)
    buildSNPdb = models.BooleanField(default=False)
    first_time = models.BooleanField(default=True)

    DATA_CHOICES = (('0', 'F'), ('1', 'C'), ('2', 'R'), ('3', 'F+C'), ('4', 'F+R'), ('5', 'C+R'), ('6', 'F+C+R'),
                    ('7', 'realignment'))
    data = models.CharField(choices=DATA_CHOICES, max_length=20)

    READS_CHOICES = (('1', 'single_reads'), ('2', 'paired_reads'), ('3', 'both'))
    reads = models.CharField(max_length=20, choices=READS_CHOICES)

    TREE_CHOICES = (('0', 'None'), ('1', 'FastTree'), ('2', 'RAxML'), ('3', 'both'))
    tree = models.CharField(max_length=20, choices=TREE_CHOICES)

    bootstrap = models.BooleanField(default=False)
    N = models.IntegerField(default=100)

    POS_CHOICES = (('0', 'None'), ('1', 'PAML'), ('2', 'HyPhy'), ('3', 'both'))
    pos_select = models.CharField(max_length=20, choices=POS_CHOICES)

    CODE_CHOICES = (('0', 'Bacteria'), ('1', 'Virus'))
    code = models.CharField(max_length=20, choices=CODE_CHOICES)

    clean = models.BooleanField(default=False)
    threads = models.IntegerField(default=2)
    cutoff = models.FloatField(default=0.1)
