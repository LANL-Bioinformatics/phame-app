#!/usr/bin/env perl

use strict;
use warnings;
use Test::More;
use FindBin qw($Bin $RealBin);
use lib "$RealBin/../lib/";
use PhaME;

# Verify module can be included via "use" pragma
BEGIN { use_ok('PhaME') }

# Verify module can be included via "require" pragma
require_ok('PhaME');


my @remove_list = PhaME::filter_genomes("test/ecoli_workdir/sketch_output.txt",
                                "test/ecoli_ref/GCA_000010245.1_ASM1024v1_genomic.fna",
                                 97.5,"test/ecoli_workdir/");


my @exp_genome = ("GCA_000013305_1_ASM1330v1_genomic.fna");
my $remove_list_len;
$remove_list_len = @remove_list;
is_deeply(\@remove_list, \@exp_genome, "test if it adds the correct genome in remove list");
is($remove_list_len, 1, "test if the length of the array is as expected");
done_testing();