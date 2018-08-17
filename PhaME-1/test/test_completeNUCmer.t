#!/usr/bin/env perl  

use strict;
use warnings;
use FindBin qw($Bin $RealBin);
use lib "$RealBin/../lib/";
use Test::More;
use lib "$Bin";
use lib "$RealBin/../ext/lib/perl5";
use File::Basename;
use PhaME;
# use Cwd;
use feature 'signatures';
use Test::Exception;

$| = 1;

# set up environments
$ENV{PATH} = "$RealBin:$RealBin/../src:$ENV{PATH}";

sub completeNUCmer ($reference, $workdir, $bindir,
					$list, $code, $thread, $error, $log, $buildSNPdb,
					$cutoff){
    my $outdir     = $workdir . '/results';
    mkdir $outdir unless -d $outdir;

    if ( -f $error ) { }
    else {
        # Create the file if it doesn't exist
        print $error;
        open( my $er, ">", $error ) or die "Could not open '$error' $!";
        close $er;
    }
    if ( -f $log ) { }
    else {
        # Create the file if it doesn't exist
        print $log;
        open( my $lg, ">", $log ) or die "Could not open '$error' $!";
        close $lg;
    }

    print "\n";
    my $nucmer
        = "runNUCmer.pl -r $reference -q $workdir -d $outdir -t $thread -l $list -c $code -b $buildSNPdb -f $cutoff  2>$error > $log\n\n";
    print $nucmer;
    if ( system($nucmer) ) { die "Error running $nucmer.\n"; }
}



completeNUCmer(
    my $reference = "test/ecoli_workdir/files/GCA_000010245_1_ASM1024v1_genomic.fna",
    my $workdir = "test/ecoli_workdir",
    my $bindir="src",
    my $list="test/ecoli_workdir/fasta_list.txt",
    my $code="bacteria",
    my $thread=4,
    my $error="test/ecoli.error",
    my $log="test/ecoli_PhaME.log",
    my $buildSNPdb=0,
    my $cutoff=98
);


done_testing();
