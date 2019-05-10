#!/usr/bin/perl
#
# check_rsync  -  Check Rsync and modules availability
# Version: 1.02
#
# Copyright (C) 2006-2008 Thomas Guyot-Sionnest <tguyot@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

use POSIX;
use strict;
use strict;
use Getopt::Long;

use vars qw($opt_H $opt_p $opt_m);
use vars qw($PROGNAME %RSYNCMSG $cpid);
use lib "/usr/local/nagios/libexec";
use utils qw($TIMEOUT %ERRORS);

$PROGNAME = "check_rsync";
$ENV{'PATH'}='';
$ENV{'BASH_ENV'}='';
$ENV{'ENV'}='';
%RSYNCMSG = (
  '0' => 'Success',
  '1' => 'Syntax or usage error',
  '2' => 'Protocol incompatibility',
  '3' => 'Errors selecting input/output files, dirs',
  '4' => 'Requested action not supported',
  '5' => 'Error starting client-server protocol',
  '6' => 'Daemon unable to append to log-file',
  '10' => 'Error in socket I/O',
  '11' => 'Error in file I/O',
  '12' => 'Error in rsync protocol data stream',
  '13' => 'Errors with program diagnostics',
  '14' => 'Error in IPC code',
  '20' => 'Received SIGUSR1 or SIGINT',
  '21' => 'Some error returned by waitpid()',
  '22' => 'Error allocating core memory buffers',
  '23' => 'Partial transfer due to error',
  '24' => 'Partial transfer due to vanished source files',
  '25' => 'The --max-delete limit stopped deletions',
  '30' => 'Timeout in data send/receive',
);
$cpid = 0;

Getopt::Long::Configure('bundling');
GetOptions (
  "H=s" => \$opt_H, "hostname=s" => \$opt_H,
  "p=s" => \$opt_p, "port=s" => \$opt_p,
  "m=s@" => \$opt_m, "module=s@" => \$opt_m );

unless (defined($opt_H)){
  print "Usage: $PROGNAME -H <host> [-p <port>] [-m <module>[,<user>,<password>] [-m <module>[,<user>,<password>]...]]\n";
  exit $ERRORS{'UNKNOWN'};
}

my $host = $opt_H;
my $port = defined($opt_p) ? $opt_p : 873;
my $verbose = 0; # Not implemented as argument yet

# Create an array for each -m arguments and store them in @modules
my @modules;
if (defined($opt_m)) {
  for(@$opt_m) {
    my @tmpmod = split(/,/);
    my ($modname, $username) = @tmpmod;
    my $pass = join(',', splice(@tmpmod, 2));
    print STDERR "Adding module $modname\n" if ($verbose);
    if ($pass) {
      print STDERR "Module $modname using authentication ($username, $pass)\n" if ($verbose > 2);
      push @modules, [ $modname, $username, $pass ];
      } else {
      push @modules, [ $modname ];
    }
  }
}

# Just in case of problems, let's not hang Nagios
$SIG{'ALRM'} = sub {
  print "CRITICAL: Rsync timed out\n";
  kill SIGKILL, $cpid if ($cpid);
  exit $ERRORS{"CRITICAL"};
};

# Rsync arguments
my $source = "rsync://$host";

alarm($TIMEOUT);

# Get a list of modules to see if rsync is up
my $command = "/usr/bin/rsync --port=$port $source";

# Workaround to kill stale rsync processes
$cpid = open(RSYNC, "$command|") or report_error("Unable to execute rsync: $!");
my $result;
{
  local $/;
  $result = <RSYNC>;
}
close(RSYNC);
my $error_code = $?;

#Turn off alarm
alarm(0);
$cpid = 0;

my $realerr = $error_code >> 8;
report_error("Rsync command $command failed with error " . $realerr . ": " . (defined $RSYNCMSG{"$realerr"} ? $RSYNCMSG{"$realerr"} : "Unknown error")) if ($realerr != 0);

# If one or more -m, check if these modules exists first...
if (@modules) {

  my @result = split(/\n/, $result);

  foreach my $mod (@modules) {
    my $match = 0;
    for (@result) {
      $match = 1 if (/^$$mod[0]\s/);
    }
    report_error("Module $$mod[0] not found") if ($match == 0);
  }
} else { # else just return OK
  print "OK: Rsync is up\n";
  exit $ERRORS{'OK'};
}

# Check each -m aruments...
for my $arg (@modules) {
  if (defined($$arg[1]) and defined($$arg[2])) {
    $source = "rsync://$$arg[1]" . '@' . "$host/$$arg[0]";
    $ENV{'RSYNC_PASSWORD'} = $$arg[2];
  } else {
    $source = "rsync://$host/$$arg[0]";
    $ENV{'RSYNC_PASSWORD'} = '';
  }

  alarm($TIMEOUT);

  # Better safe than sorry...
  undef $error_code;
  undef $result;
  # Get a file listing of the root of the module
  $command = "/usr/bin/rsync --port=$port $source";

  # Workaround to kill stale rsync processes
  $cpid = open(RSYNC, "$command|") or report_error("Unable to execute rsync: $!");
  {
    local $/;
    $result = <RSYNC>;
  }
  close(RSYNC);
  $error_code = $?;

  #Turn off alarm
  alarm(0);
  $cpid = 0;

  $realerr = $error_code >> 8;
  report_error("Rsync command failed on module $$arg[0] with error " . $realerr . ": " . (defined $RSYNCMSG{$realerr} ? $RSYNCMSG{$realerr} : "Unknown error")) if ($realerr != 0);
}

if (@modules > 0) {
  print "OK: Rsync is up with ", scalar(@modules), " module tested\n" if (@modules == 1);
  print "OK: Rsync is up with ", scalar(@modules), " modules tested\n" if (@modules > 1);
  exit $ERRORS{'OK'};
} else { # We hould never end up here :)
  print "UNKNOWN: The unexpected occured (bug?)\n";
  exit $ERRORS{'UNKNOWN'};
}

# Report error passed as one string, print rsync messages to STDERR
sub report_error {
  my $report = shift;
  print "CRITICAL: $report\n";
  exit $ERRORS{'CRITICAL'};
}

