from django.db import models

# Create your models here.
class Run(models.Model):
    ref_dir = models.FileField(null=True, upload_to='refdir')
    work_dir = models.FileField(null=True, upload_to='workdir')

    REF_CHOICES = (('random', '0'), ('given', '1'), ('ANI', '2'))
    reference = models.CharField(max_length=6, choices=REF_CHOICES)

    ref_file = models.FileField(null=True)
    project = models.CharField(max_length=20, default='ecoli')
    CDS_CHOICES = (('0', '0'), ('1', '1'))
    cds_snps = models.CharField(max_length=1, default=False)

    BOOL_CHOICES = (('0', '0'), ('1', '1'))
    buildSNPdb = models.CharField(max_length=1, choices=BOOL_CHOICES)
    FIRST_CHOICES = (('1', '1'), ('2', '2'))
    first_time = models.CharField(max_length=3, choices=FIRST_CHOICES)

    DATA_CHOICES = (('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'),
                    ('7', '7'))
    data = models.CharField(choices=DATA_CHOICES, max_length=20)

    READS_CHOICES = (('1', '1'), ('2', '2'), ('3', '3'))
    reads = models.CharField(max_length=20, choices=READS_CHOICES)

    TREE_CHOICES = (('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'))
    tree = models.CharField(max_length=20, choices=TREE_CHOICES)

    bootstrap = models.CharField(max_length=3, choices=BOOL_CHOICES)
    N = models.IntegerField(default=100)

    POS_CHOICES = (('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'))
    pos_select = models.CharField(max_length=20, choices=POS_CHOICES)

    CODE_CHOICES = (('0', '0'), ('1', '1'))
    code = models.CharField(max_length=20, choices=CODE_CHOICES)

    clean = models.CharField(max_length=3, choices=BOOL_CHOICES)
    threads = models.IntegerField(default=2)
    cutoff = models.FloatField(default=0.1)
