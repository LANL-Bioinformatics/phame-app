#!/usr/bin/env perl

use strict;
use File::Basename;
use diagnostics;
use FindBin qw($RealBin);
# use lib "$RealBin/../ext/lib/perl5";
# use lib "$RealBin/../lib";
use Statistics::Distributions;

my $dir     = shift @ARGV;
my $nssites = shift @ARGV;
my @nssite;
my $site;
my %gene;
my @genes;
my ( $np, $lnL, $w, $p0, $p1, $w0, $w1 );
my ( $p2, $w2 );
my ( $p2a, $p2b, $w2a, $w2b );
my $model = 0;

# removing , from ns sites and adding it to list
if ( $nssites =~ /,/ ) { @nssite = split ",", $nssites; }

# create and open output file
my $outfile = $dir . '/PAMLsitesResults_long.txt';
open( OUT, ">$outfile" ) || die "$!";

# for printing the first row
foreach (@nssite) {
   print "$_\n";
    # a column for M0 and three columns
    if ( $_ == 0 ) { print OUT "\tM$_\t\t"; }
    # a column for M1
    if ( $_ < 2 && $_ > 0 ) { print OUT "\tM$_\t\t\t\t\t"; }
    # additional columns for M2 and higher
    if ( $_ > 1 ) { print OUT "\tM$_\t\t\t\t\t\t\t"; }
}
# print out columns to put information with Branch length
print OUT "\tM0Br\nGene\t";
foreach (@nssite) {
    # to add columns for adding np (parameters), lnl, w, and proportions
    if ( $_ == 0 ) { print OUT "np\tlnL\tw\t"; }
    if ( $_ < 2 && $_ > 0 ) { print OUT "np\tlnL\tw0\tw1\tp0\tp1\t"; }
    if ( $_ > 1 ) { print OUT "np\tlnL\tw0\tw1\tw2\tp0\tp1\tp2\t"; }
}
# print OUT "\tnp\tlnL\tw0\tw1\tw2a\tw2b\tp0\tp1\tp2a\tp2b\t";
print OUT "np\tlnL\n";

# open pamldir, directory named paml
opendir( DIR, "$dir" ) || die "$!";

foreach my $files ( sort { $b cmp $a } readdir(DIR) ) {
   if ( $files =~ /.*\.Sites$/ ) {
      # $model = 0;
      my ( $name, $path, $suffix ) = fileparse( "$files", qr/\.[^.]*/ );
      $site = $dir . '/' . $files;
      # if file exists and is not empty
      if ( -s $site ) {
         print OUT "\n$name\t";
         push @genes, $name;
         open( IN, "$site" ) || die "$!";
         while (<IN>) {
            if (/Model\s*(\d):\s*/) { $model = $1; }
            if (/^lnL\(.+np:\s*(\d+)\):\s*(-\S+)/) {
               ( $np, $lnL ) = ( $1, $2 );
               $gene{"$model:np"}{$name}  = $np;
               $gene{"$model:lnL"}{$name} = $lnL;
               print OUT "$np\t$lnL\t";
                }
                # print $model;
                if ( $model == 0 ) {
                    if (/^omega.+=\s*(\S+)/) {
                        $w = $1;
                        print OUT "$w\t";
                    }
                }
                if ( $model < 2 && $model > 0 ) {
                    if (/^p:\s*(\S+)\s*(\S+)/) { ( $p0, $p1 ) = ( $1, $2 ); }
                    if (/^w:\s*(\S+)\s*(\S+)/) {
                        ( $w0, $w1 ) = ( $1, $2 );
                        print OUT "$w0\t$w1\t";
                        print OUT "$p0\t$p1\t";
                    }
                }
                if ( $model > 1 ) {
                    if (/^p:\s*(\S+)\s*(\S+)\s*(\S*)/) {
                        ( $p0, $p1, $p2 ) = ( $1, $2, $3 );
                    }
                    if (/^w:\s*(\S+)\s*(\S+)\s*(\S*)/) {
                        ( $w0, $w1, $w2 ) = ( $1, $2, $3 );
                        print OUT "$w0\t$w1\t$w2\t";
                        print OUT "$p0\t$p1\t$p2\t";
                    }
                }
            }
        }
    }

    elsif ( $files =~ /.*\.BrSites$/ ) {
        $model = "BR";
        my ( $name, $path, $suffix ) = fileparse( "$files", qr/\.[^.]*/ );
        # if ( $name =~ /.*_(\d+)$/ ) { $model .= $1; }
        $site = $dir . '/' . $files;
        if ( -s $site ) {
            # print OUT "\t";
            # print
                # "\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t$name\t";
            # push @genes, $name;
            open( IN, "$site" ) || die "$!";
            while (<IN>) {
                if (/^lnL\(.+np:\s*(\d+)\):\s*(-\S+)/) {
                    ( $np, $lnL ) = ( $1, $2 );
                    $gene{"$model:np"}{$name}  = $np;
                    $gene{"$model:lnL"}{$name} = $lnL;
                    print OUT "$np\t$lnL\t";

     #               print "$model:np\t$name\t$np\n$model:lnL\t$name\t$lnL\n";
                }
                if (/^proportion\s*(\S+)\s*(\S+)\s*(\S*)\s*(\S*)/) {
                    ( $p0, $p1, $p2a, $p2b ) = ( $1, $2, $3, $4 );
                }
                if (/^foreground w\s*(\S+)\s*(\S+)\s*(\S*)\s*(\S*)/) {
                    ( $w0, $w1, $w2a, $w2b ) = ( $1, $2, $3, $4 );
                    print "$w0\t$w1\t$w2a\t$w2b\t";
                    print "$p0\t$p1\t$p2a\t$p2b\t";
                    # print OUT "$w0\t$w1\t$w2a\t$w2b\t";
                    # print OUT "$p0\t$p1\t$p2a\t$p2b\t";
                }
            }
        }
    }
}
close OUT;
closedir DIR;


##############################################################################
$outfile = $dir . '/PAMLsitesResults.txt';
open( OUT2, ">$outfile" ) || die "$!";

print OUT2
    "\tM0\t\tM1a\t\tM2a\t\tM7\t\tM8\t\tM0Br\t\tM0-M0Br\t\tM0-M1a\t\t\tM1a-M2a\t\t\tM7-M8\n";
print OUT2
   "Genes\tlnL\tnp\tlnL\tnp\tlnL\tnp\tlnL\tnp\tlnL\tnp\tlnL\tnp\tp\t2lnL\tp-value\tp\t2lnL\tp-value\tp\t2lnL\tp-value\tp\t2lnL\tp-value";
my $df0;
my $lnl0;
my $df1;
my $lnl1;
my $df2;
my $lnl2;
my $df7;
my $lnl7;
my $df8;
my $lnl8;
my $dfa;
my $lnla;

foreach my $entry (@genes) {
    #if ( $entry =~ /.+_\d+$/ ) {
    #    print OUT "\n\t\t\t\t\t\t\t\t\t\t\t$entry\t";
    #    print "$entry\n";
    #}
    #else { print OUT "\n$entry\t"; }
    print OUT2 "\n$entry\t"; # prints the name of the gene in first column
    undef $df0;
    undef $lnl0;
    undef $df1;
    undef $lnl1;
    undef $df2;
    undef $lnl2;
    undef $df7;
    undef $lnl7;
    undef $df8;
    undef $lnl8;
    undef $dfa;
    undef $lnla;

    foreach my $stat ( sort keys %gene ) {
        print "$stat\n";
        if ( defined $gene{$stat}{$entry} ) {
            print OUT2 "$gene{$stat}{$entry}\t"; # prints lnl from all models and genes
            if ( $stat =~ /0:lnL/ )  { $lnl0 = $gene{$stat}{$entry}; }
            if ( $stat =~ /0:np/ )   { $df0  = $gene{$stat}{$entry}; }
            if ( $stat =~ /1:lnL/ )  { $lnl1 = $gene{$stat}{$entry}; }
            if ( $stat =~ /1:np/ )   { $df1  = $gene{$stat}{$entry}; }
            if ( $stat =~ /2:lnL/ )  { $lnl2 = $gene{$stat}{$entry}; }
            if ( $stat =~ /2:np/ )   { $df2  = $gene{$stat}{$entry}; }
            if ( $stat =~ /7:lnL/ )  { $lnl7 = $gene{$stat}{$entry}; }
            if ( $stat =~ /7:np/ )   { $df7  = $gene{$stat}{$entry}; }
            if ( $stat =~ /8:lnL/ )  { $lnl8 = $gene{$stat}{$entry}; }
            if ( $stat =~ /8:np/ )   { $df8  = $gene{$stat}{$entry}; }
            if ( $stat =~ /BR:lnL/ ) { $lnla = $gene{$stat}{$entry}; }
            if ( $stat =~ /BR:np/ )  { $dfa  = $gene{$stat}{$entry}; }
        }
    }
    #if   ( $entry =~ /.+_\d+$/ ) { print OUT2 "\t\t\t\t\t\t"; }
    #else                         { print OUT2 "\t\t\t"; }
    # print OUT2 "\t\t"; 

    if ( defined $lnl0 && defined $lnla && defined $df0 && defined $dfa ) {
        my $p = $dfa - $df0;
        my $lnl = abs( 2 * ( $lnla - $lnl0 ) );
        if ( $lnl < 0 ) { $lnl = sprintf( "%.5e", $lnl ); }
        my $chisprob = Statistics::Distributions::chisqrprob( $p, $lnl );
        if ( $chisprob < 0 || $chisprob < 0.0001 ) {
            $chisprob = sprintf( "%.5e", $chisprob );
        }
        print OUT2 "$p\t$lnl\t", $chisprob, "\t";
    }

    if ( defined $lnl0 && defined $lnl1 && defined $df0 && defined $df1 ) {
        my $p = $df1 - $df0;
        my $lnl = abs( 2 * ( $lnl1 - $lnl0 ) );
        if ( $lnl < 0 ) { $lnl = sprintf( "%.5e", $lnl ); }
        my $chisprob = Statistics::Distributions::chisqrprob( $p, $lnl );
        if ( $chisprob < 0 || $chisprob < 0.0001 ) {
            $chisprob = sprintf( "%.5e", $chisprob );
        }
        print OUT2 "$p\t$lnl\t", $chisprob, "\t";
    }
    if ( defined $lnl1 && defined $lnl2 && defined $df1 && defined $df2 ) {
        my $p = $df2 - $df1;
        my $lnl = abs( 2 * ( $lnl2 - $lnl1 ) );
        if ( $lnl < 0 ) { $lnl = sprintf( "%.5e", $lnl ); }
        my $chisprob = Statistics::Distributions::chisqrprob( $p, $lnl );
        if ( $chisprob < 0 || $chisprob < 0.0001 ) {
            $chisprob = sprintf( "%.5e", $chisprob );
        }
        print OUT2 "$p\t$lnl\t", $chisprob, "\t";
    }
    if ( defined $lnl7 && defined $lnl8 && defined $df7 && defined $df8 ) {
        my $p        = $df8 - $df7;
        my $lnl      = abs( 2 * ( $lnl8 - $lnl7 ) );
        my $chisprob = Statistics::Distributions::chisqrprob( $p, $lnl );
        if ( $chisprob < 0 || $chisprob < 0.0001 ) {
            $chisprob = sprintf( "%.5e", $chisprob );
        }
        print OUT2 "$p\t$lnl\t", $chisprob, "\t";
    }
}
close OUT2;

