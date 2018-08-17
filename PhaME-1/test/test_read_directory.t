#!/usr/bin/env perl
use strict;
use warnings;
use FindBin qw($Bin $RealBin);
use lib "$RealBin/../lib/";
use File::Basename;
use Test::More;

# Verify module can be included via "use" pragma
BEGIN { use_ok('misc_funcs') }

# Verify module can be included via "require" pragma
require_ok('misc_funcs');

my @skips = ("GCA_000010385_1_ASM1038v1_genomic.fna", "GCA_000013305_1_ASM1330v1_genomic.fna",
                       "GCA_000027125_1_ASM2712v1_genomic.fna",
                       "GCA_000010245_1_ASM1024v1_genomic.fna",
                       "GCA_000012005_1_ASM1200v1_genomic.fna",
                       "GCA_000026345_1_ASM2634v1_genomic.fna");

my @keep_genome = misc_funcs::read_directory("test/ecoli_workdir", @skips);
my @expected_keep_genome = ('test/ecoli_workdir/files/GCA_000008865_1_ASM886v1_genomic.fna');
is_deeply(\@keep_genome, \@expected_keep_genome, "Test if it gives a list of genomes minus the ones in the given list.");
done_testing();
