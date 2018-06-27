from django.db import models

# Create your models here.
class Run(models.Model):
    ref_dir = models.FilePathField(null=True)
    work_dir = models.FilePathField(null=True)

    RANDOM = '0'
    GIVEN = '1'
    ANI = '2'
    REF_CHOICES = ((RANDOM, 'random'), (GIVEN, 'given'), (ANI, 'ANI'))
    reference = models.CharField(max_length=6, choices=REF_CHOICES)

    ref_file = models.FileField(null=True)
    project = models.CharField(max_length=20, default='ecoli')

    NO_CDS = '0'
    CDS_SNPS = '1'
    CDS_CHOICES = ((NO_CDS, 'no cds SNPs'), (CDS_SNPS, 'cds SNPs'))
    cds_snps = models.CharField(max_length=20, choices=CDS_CHOICES)

    NO = '0'
    YES = '1'
    BOOL_CHOICES = ((NO, 'no'), (YES, 'yes'))

    ALIGN = '0'
    BUILD = '1'
    BUILD_CHOICES = ((ALIGN, 'only align to reference'), (BUILD, 'build SNP database'))
    buildSNPdb = models.CharField(max_length=40, choices=BUILD_CHOICES)

    FIRST = '1'
    UPDATE_ALIGNMENT = '2'
    FIRST_CHOICES = ((FIRST, 'yes'), (UPDATE_ALIGNMENT, 'update existing SNP alignment'))
    first_time = models.CharField(max_length=40, choices=FIRST_CHOICES)

    F = '0'
    C = '1'
    R = '2'
    F_C = '3'
    F_R = '4'
    C_R = '5'
    F_C_R = '6'
    REALIGNMENT = '7'
    DATA_CHOICES = ((F, 'F'), (C, 'C'), (R, 'R'), (F_C, 'F+C'), (F_R, 'F+R'), (C_R, 'C+R'), (F_C_R, 'F+C+R'),
                    (REALIGNMENT, 'realignment'))
    data = models.CharField(choices=DATA_CHOICES, max_length=20)

    SINGLE_READS = '0'
    PAIRED_READS = '1'
    BOTH = '2'
    READS_CHOICES = ((SINGLE_READS, 'single reads'), (PAIRED_READS, 'paired reads'), (BOTH, 'both'))
    reads = models.CharField(max_length=20, choices=READS_CHOICES)

    BOWTIE = 'bowtie'
    FASTTREE_ALIGNER = 'FastTree'
    MINIMAP2 = 'minimap2'
    ALIGNER_CHOICES = ((BOWTIE, 'bowtie'), (FASTTREE_ALIGNER, 'FastTree'), (MINIMAP2, 'minimap2'))
    aligner = models.CharField(max_length=20, choices=ALIGNER_CHOICES, default=BOWTIE)

    NO_TREE = '0'
    FASTTREE = '1'
    RAXML = '2'
    BOTH_TREES = '3'
    TREE_CHOICES = ((NO_TREE, 'no tree'), (FASTTREE, 'FastTree'), (RAXML, 'RAxML'), (BOTH_TREES, 'both'))
    tree = models.CharField(max_length=20, choices=TREE_CHOICES)

    bootstrap = models.CharField(max_length=3, choices=BOOL_CHOICES)
    N = models.IntegerField(default=100)

    NO_POS = '0'
    PAML = '1'
    HYPHY = '2'
    BOTH_POS = '3'
    POS_CHOICES = ((NO_POS, 'no'), (PAML, 'PAML'), (HYPHY, 'HyPhy'), (BOTH_POS, 'both'))
    pos_select = models.CharField(max_length=20, choices=POS_CHOICES)

    BACTERIA = '0'
    VIRUS = '1'
    CODE_CHOICES = ((BACTERIA, 'Bacteria'), (VIRUS, 'Virus'))
    code = models.CharField(max_length=20, choices=CODE_CHOICES)

    clean = models.CharField(max_length=3, choices=BOOL_CHOICES)
    threads = models.IntegerField(default=2)
    cutoff = models.FloatField(default=0.1)

class ReferenceFile(models.Model):
    run = models.ForeignKey(Run, on_delete=models.CASCADE)
    ref_file = models.FileField(upload_to='refdir')


class WorkFile(models.Model):
    run = models.ForeignKey(Run, on_delete=models.CASCADE)
    work_file = models.FileField(upload_to='workdir')
