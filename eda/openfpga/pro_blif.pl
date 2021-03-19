#!usr/bin/perl -w

# This script comes from OpenFPGA:
# https://github.com/lnis-uofu/OpenFPGA/blob/master/openfpga_flow/scripts/pro_blif.pl

use strict;
#use Shell;
use FileHandle;
#Use the time
use Time::gmtime;

#Get Date
my $mydate = gmctime();
my ($char_per_line) = (80);

my ($fname,$frpt,$finitial);
my $add_default_clk = "off";
my $latch_token;
my ($remove_buffers) = (0);
my ($default_clk_name) = ("clk");
my @buffers_to_remove;
my @buffers_to_rename;

sub print_usage()
{
  print "Usage:\n";
  print "      perl <script_name.pl> [-options]\n";
  print "      Options:(Mandatory!)\n";
  print "              -i <input_blif_path>\n";
  print "              -o <output_blif_path>\n";
  print "      Options: (Optional)\n";
  print "              -remove_buffers: remove buffers in the blif\n";
  print "              -add_default_clk: add a default clock using the default clock name 'clk', or set by users through the option '-default clk'\n";
  print "              -default_clk <clk_name>: set the default clk name to be used by .latch\n";
  print "              -initial_blif <input_blif_path>\n";
  print "\n";
  return 0;
}

sub opts_read()
{
  if (-1 == $#ARGV) {
    print "Error: No input argument!\n";
    &print_usage();
    exit(1); 
  } else {
    for (my $iargv = 0; $iargv < $#ARGV+1; $iargv++) {
      if ("-i" eq $ARGV[$iargv]) {
        $fname = $ARGV[$iargv+1];
      } elsif ("-o" eq $ARGV[$iargv]) {
        $frpt = $ARGV[$iargv+1];
      } elsif ("-add_default_clk" eq $ARGV[$iargv]) {
        $add_default_clk = "on";
      } elsif ("-default_clk" eq $ARGV[$iargv]) {
        $default_clk_name = $ARGV[$iargv+1];
      } elsif ("-initial_blif" eq $ARGV[$iargv]) {
        $finitial = $ARGV[$iargv+1];
      } elsif ("-remove_buffers" eq $ARGV[$iargv]) {
        $remove_buffers = 1;
      }
    }
  } 
  return 0;
}

# Print a line of blif netlist
sub fprint_blifln($ $ $) {
  my ($FH, $tokens_ref, $char_per_line) = @_;
  my ($cur_line_len) = (0);
  my @tokens = @$tokens_ref;
  
  if ($char_per_line < 1) {
    die "ERROR: (fprint_blifln) minimum acceptable number of chars in a line is 1!\n";
  } 
  # if the length of current line exceed the char_per_line,
  # A continue line '\' is added and start a new line 
  for (my $itok = 0; $itok < ($#tokens+1); $itok++) {
    if (!($tokens[$itok])) {
      next;
    }
    # Contain any buffer names to be removed won't show up
    if (1 == $remove_buffers) {
      for (my $ibuf = 0; $ibuf < $#buffers_to_remove + 1; $ibuf++) {
        if ($tokens[$itok] eq $buffers_to_remove[$ibuf]) {
          $tokens[$itok] = $buffers_to_rename[$ibuf];
        }
      }
    }
    $cur_line_len += length($tokens[$itok]);
    if ($cur_line_len > $char_per_line) {
      print $FH "\\"."\n";
      $cur_line_len = 0;
    }
    print $FH "$tokens[$itok] "; 
    $cur_line_len += length($tokens[$itok]);
  }
  print $FH "\n";
  
}

sub read_blifline($ $) {
  my ($FIN, $line_no_ptr) = @_;
  my ($lines,$line) = ("","");
  
  # Get one line
  if (defined($line = <$FIN>)) {
    chomp $line;
    $lines = $line;
    # Replace the < and > with [ and ], VPR does not support...
    $lines =~ s/</[/g;
    $lines =~ s/>/]/g;
    while($lines =~ m/\\$/) {
      $lines =~ s/\\$//;
      if (defined($line = <$FIN>)) {
        chomp $line;
        $lines = $lines.$line;
        $line =~ s/</[/g;
        $line =~ s/>/]/g;
      } else {
        return $lines;
      }
    }
    return $lines;
  } else {
    return $lines;
  }

}

sub process_blifmodel($ $) {
  my ($FIN,$line_no_ptr) = @_;
  my ($blackbox) = (0);
  my ($lines);
  my ($clk_num,$have_default_clk,$need_default_clk,$clk_recorded) = (0,0,0,0);
  my @model_input_tokens;
  my ($input_lines);

  while(!eof($FIN)) {
    # Get one line
    $lines = &read_blifline($FIN,$line_no_ptr);
    # Check the tokens
    if (!defined($lines)) {
      next;
    }
    my @tokens = split('\s+',$lines);
    # .end -> return
    if (!defined($tokens[0])) {
      next;
    }
    if (".end" eq $tokens[0]) {
      return (\@model_input_tokens,$blackbox,$clk_num,$have_default_clk,$need_default_clk);
    } elsif (".inputs" eq $tokens[0]) {
      foreach my $temp(@tokens) {
        if ($temp eq $default_clk_name) {
          $have_default_clk = 1;
          $clk_num++;
          print "Found 1 clock: $temp in @tokens\n";
          last;
        }
      }
      @model_input_tokens = @tokens;
    } elsif (".blackbox" eq $tokens[0]) {
      $blackbox = 1;
    } elsif (".latch" eq $tokens[0]) {
      # illegal definition exit
      if ((3 != $#tokens)&&(5 != $#tokens)) {
        die "ERROR: [LINE: $$line_no_ptr]illegal definition of latch!\n";
      } elsif (3 == $#tokens) {
        # We need a default clock
        if ($need_default_clk == 0) {
          $need_default_clk = 1;
          $clk_num++;
        }
      } elsif (5 == $#tokens) {
        $clk_recorded = 0;
        # Check if we have this clk names already
        foreach my $tmp(@model_input_tokens) {
          if ($tmp eq $tokens[4]) {
            $clk_recorded = 1;
            last;
          } 
        }
        # if have been recorded, we push it into the array
        if (0 == $clk_recorded) {
          $clk_num++;
          push @model_input_tokens,$tokens[4];
        }
      }
    # Could be subckt or .names
    } elsif (".names" eq $tokens[0]) {
      if ((3 == ($#tokens + 1))&&(1 == $remove_buffers)) {  
        # We want to know is this a buffer???
        my $lut_lines = &read_blifline($FIN,$line_no_ptr);
        my @lut_lines_tokens = split('\s+',$lut_lines);
        if ((2 == ($#lut_lines_tokens + 1))&&("1" eq $lut_lines_tokens[0])&&("1" eq $lut_lines_tokens[1])) {
          # push it to the array: buffers_to_remove
          push @buffers_to_remove,$tokens[1]; 
          push @buffers_to_rename,$tokens[2]; 
        }
      }
    }
  }
  # Re-organise the input lines
  #print @model_input_tokens;
  $input_lines = ".inputs ";
  foreach my $temp(@model_input_tokens) {
    if (".inputs" ne $temp) {
      $input_lines .= $temp." ";
    }
  }
  $input_lines =~ s/\s+$//;
  @model_input_tokens = split('\s+',$input_lines); 
  
  return (\@model_input_tokens,$blackbox,$clk_num,$have_default_clk,$need_default_clk);
}

sub scan_blif()
{
  my ($line,$lines);
  my @tokens;
  my ($clk_num,$have_default_clk,$need_default_clk,$clk_recorded);
  my ($blackbox,$model_clk_num);
  my @input_tokens;
  my $input_lines;
  my (@input_buffer);
  my ($line_no) = (0);

  if (!defined($finitial)) {
    $latch_token = "re $default_clk_name";
  } else {
    my $latch_token_found = 0;
    my $count = 0;
    my ($FIN0) = FileHandle->new;
    if ($FIN0->open("< $finitial")) {
      print "INFO: Parsing $finitial...\n";
    } else {
       die "ERROR: Fail to open $finitial!\n";
    }
    while((!$latch_token_found)&&(!eof($FIN0))){
      # Get one line
      $lines = &read_blifline($FIN0);
      if (!defined($lines)) {
        next;
      }
      @tokens = split('\s+',$lines);
      if(".latch" eq $tokens[0]) {
        if($#tokens == 5){
          $latch_token = "$tokens[3] $tokens[4]";
          $latch_token_found = 1;
        }
      }
    }
    close($FIN0);
  }
  
  # Pre-process the netlist
  # Open src file first-scan to check if we have clock
  my ($FIN) = FileHandle->new;
  if ($FIN->open("< $fname")) {
    print "INFO: Parsing $fname...\n";
  } else {
     die "ERROR: Fail to open $fname!\n";
  }
  while(!eof($FIN)) {
    # Get one line
    $lines = &read_blifline($FIN);
    if (!defined($lines)) {
      next;
    }
    @tokens = split('\s+',$lines);
    if (!defined($tokens[0])) {
      next;
    }
    # When we found .model we should check it. until .end comes. 
    # Check if it is a black box
    if (".model" eq $tokens[0]) {
      ($input_lines,$blackbox,$model_clk_num,$have_default_clk,$need_default_clk) = &process_blifmodel($FIN,\$line_no);
      if (0 == $blackbox) {
        @input_tokens = @$input_lines;
      }
      $clk_num += $model_clk_num;
    }
  }
  close($FIN);

  # Add default clock
  if ("on" eq $add_default_clk) {
    print "INFO: $clk_num clock ports need to be added.\n";
    print "INFO: have_default_clk: $have_default_clk, need_default_clk: $need_default_clk\n";
    if ((0 == $have_default_clk)&&(1 == $need_default_clk)) {
      push @input_tokens,$default_clk_name;
    }
  }
  # Bypass some sensitive tokens
  for(my $itok = 0; $itok < $#input_tokens+1; $itok++) {
    if ("unconn" eq $input_tokens[$itok]) {
      delete $input_tokens[$itok];
    }
  }
  # Print Buffer names to be removed
  my $num_buffer_to_remove = $#buffers_to_remove + 1;
  print "INFO: $num_buffer_to_remove buffer to be removed:\n";
  for(my $itok = 0; $itok < $#buffers_to_remove+1; $itok++) {
    print $buffers_to_remove[$itok]." will be renamed to ".$buffers_to_rename[$itok]."\n";
  }


  # Second scan - write
  my ($inputs_written) = (0);
  my ($FIN2) = FileHandle->new;
  if ($FIN2->open("< $fname")) {
    print "INFO: Parsing $fname the second time...\n";
  } else {
     die "ERROR: Fail to open $fname!\n";
  }
  # Open des file
  my ($FOUT) = (FileHandle->new);
  if (!($FOUT->open("> $frpt"))) {
    die "Fail to create output file: $frpt!\n";  
  }
  while(!eof($FIN2)) {
    $line = <$FIN2>;
    chomp $line; 
    if ($line eq "") {
      print $FOUT "\n";
      next;
    }
    # Replace the < and > with [ and ], VPR does not support...
    $line =~ s/</[/g;
    $line =~ s/>/]/g;
    # Check if this line start with ".latch", which we cares only
    @tokens = split('\s+',$line);
    if ((".inputs" eq $tokens[0])&&(0 == $inputs_written)) {
      $lines = $line;
      while($lines =~ m/\\$/) {
        $line = <$FIN2>;
        chomp $line;
        # Replace the < and > with [ and ], VPR does not support...
        $line =~ s/</[/g;
        $line =~ s/>/]/g;
        $lines =~ s/\\$//;
        $lines = $lines.$line;
      }
      #print @input_tokens."\n";
      &fprint_blifln($FOUT,\@input_tokens,$char_per_line); 
      $inputs_written = 1;
      next;
    }
    if (".outputs" eq $tokens[0]) {
      $lines = $line;
      while($lines =~ m/\\$/) {
        $line = <$FIN2>;
        chomp $line;
        # Replace the < and > with [ and ], VPR does not support...
        $line =~ s/</[/g;
        $line =~ s/>/]/g;
        $lines =~ s/\\$//;
        $lines = $lines.$line;
      }
      my @output_tokens = split('\s',$lines);
      for(my $itok = 0; $itok < $#output_tokens+1; $itok++) {
        if ("unconn" eq $output_tokens[$itok]) {
          delete $output_tokens[$itok];
        }
      }
      &fprint_blifln($FOUT,\@output_tokens,$char_per_line); 
      next;

    }
    if (".latch" eq $tokens[0]) {
      # check if we need complete it
      if ($#tokens == 3) {
        # Complete it
        for (my $i=0; $i<3; $i++) {
          print $FOUT "$tokens[$i] ";
        }
        print $FOUT "$latch_token $tokens[3]\n";
      } elsif ($#tokens == 5) {
        # replace the clock name with clk
        for (my $i=0; $i < ($#tokens+1); $i++) {
        #  if (4 == $i) {
        #    print $FOUT "clk ";
        #  } else {
            print $FOUT "$tokens[$i] "; 
        #  }
        } 
        print $FOUT "\n";
      } else {
        die "ERROR: [LINE: $line_no]illegal definition of latch!\n";
      }
      next;
    } elsif (".names" eq $tokens[0]) {
      if ((3 == ($#tokens + 1))&&(1 == $remove_buffers)) {  
        # We want to know is this a buffer???
        my $lut_lines = &read_blifline($FIN2,\$line_no);
        my @lut_lines_tokens = split('\s+',$lut_lines);
        if ((2 == ($#lut_lines_tokens + 1))&&("1" eq $lut_lines_tokens[0])&&("1" eq $lut_lines_tokens[1])) {
          # pass it.
          next;
        } else {
          print $FOUT "$line\n";
          print $FOUT "$lut_lines\n";
        }
      } else {
        print $FOUT "$line\n";
      }
      next;
    } elsif ((".subckt" eq $tokens[0])&&(1 == $remove_buffers)) {
      $lines = $line;
      $lines =~ s/\s+$//;
      while($lines =~ m/\\$/) {
        $line = <$FIN2>;
        chomp $line;
        # Replace the < and > with [ and ], VPR does not support...
        $line =~ s/</[/g;
        $line =~ s/>/]/g;
        $lines =~ s/\\$//;
        $lines = $lines.$line;
        $lines =~ s/\s+$//; #ODIN II has some shit space after \ !!!!!
      }
      my @subckt_tokens = split('\s+',$lines);
      for(my $itok = 0; $itok < $#subckt_tokens+1; $itok++) {
        if (($itok > 1)&&("" ne $subckt_tokens[$itok])) {
          my @port_tokens = split('=',$subckt_tokens[$itok]);
          for (my $ibuf = 0; $ibuf < $#buffers_to_remove + 1; $ibuf++) {
            if ($port_tokens[1] eq $buffers_to_remove[$ibuf]) {
              $port_tokens[1] = $buffers_to_rename[$ibuf];
            }
          }
          $subckt_tokens[$itok] = join ('=',$port_tokens[0],$port_tokens[1]);
          #print "See:".$subckt_tokens[$itok]."\n";
        }
      }
      &fprint_blifln($FOUT,\@subckt_tokens,$char_per_line); 
       
      next;
    }
    
    print $FOUT "$line\n";
  }
  close($FIN2);
  close($FOUT);
  return 0;
}

sub main()
{
  &opts_read(); 
  &scan_blif();
  return 0;
}
 
&main();
exit(0);
