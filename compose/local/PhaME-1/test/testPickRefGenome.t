#!/usr/bin/env perl  

use strict;
use warnings;
use FindBin qw($Bin $RealBin);
use lib "$RealBin/../lib/";
use Test::More;

# Verify module can be included via "use" pragma
BEGIN { use_ok('PhaME') }

# Verify module can be included via "require" pragma
require_ok('PhaME');

my $ref_genome
    = PhaME::PickRefGenome( "test", "test/ref","test/results/ebola.error",
    "test/results/ebola_PhaME.log", "test/sketch_output.txt");
is( $ref_genome, 'test/ref/ZEBOV_2007_9Luebo.fna', "test if it picks the right reference genome" );
done_testing();
