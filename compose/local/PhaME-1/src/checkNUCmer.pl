#!/usr/bin/env perl

use strict;
use Getopt::Long;
use FileHandle;

my $infile;
my $reffile;
my $reference;
my $gap_length = 0;

GetOptions(
    'i=s'    => \$infile,
    'r=s'    => \$reffile,
    'h|help' => sub { usage() },
);

get_length($reffile);
read_gaps($infile);


sub get_length {
   # The function counts the position in a file that doesnt begin with
   # >, so it still counts other characters that
   # are not ATCG, but for the purpose here, it should be OK
   my $seq = '';
   open(my $fh, '<', $reffile);
   while (my $row = <$fh>)
      {
      chomp $row;

      if ($row =~ m/^>/)
      {
          next;
      }
      # remove trailing white spaces
      $row =~ s/^\s+|\s+$//g;
      $seq .= $row;
}

$reference = length($seq);

}


sub read_gaps {
    my $line;
    my $fh = FileHandle->new($infile) || die "$!";
    if ( $fh->open("< $infile") ) {
        $/ = "\n";
        while (<$fh>) {
            unless ($_) { next; }
            my ( $ref, $start, $end, $len, $query ) = split /\t/, $_;
            $gap_length += $len;
        }
    }
    
   my $aligned_percentage = sprintf("%.2f", (1 - ($gap_length / $reference))*100);
   print $aligned_percentage;
    # if ( $gap_proportion < 0.75 )  { print "0"; }
    # if ( $gap_proportion >= 0.75 ) { print "1"; }
}

sub usage {
    print STDERR"
Usage:
   $0 -i <gaps file> -r <reference file> 
";
    exit;
}
