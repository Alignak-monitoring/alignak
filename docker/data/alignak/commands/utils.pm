# Utility drawer for Nagios plugins.
#
# This will be deprecated soon. Please use Nagios::Plugin from CPAN
# for new plugins

package utils;

require Exporter;
@ISA = qw(Exporter);
@EXPORT_OK = qw($TIMEOUT %ERRORS &print_revision &support &usage);

#use strict;
#use vars($TIMEOUT %ERRORS);
sub print_revision ($$);
sub usage;
sub support();
sub is_hostname;

## updated by autoconf
$PATH_TO_SUDO    = "/usr/bin/sudo";
$PATH_TO_RPCINFO = "" ;
$PATH_TO_LMSTAT  = "" ;
$PATH_TO_SMBCLIENT = "" ;
$PATH_TO_MAILQ   = "";
$PATH_TO_QMAIL_QSTAT = "";

## common variables
$TIMEOUT = 15;
%ERRORS=('OK'=>0,'WARNING'=>1,'CRITICAL'=>2,'UNKNOWN'=>3,'DEPENDENT'=>4);

## utility subroutines
sub print_revision ($$) {
	my $commandName = shift;
	my $pluginRevision = shift;
	print "$commandName v$pluginRevision (nagios-plugins 2.1.1)\n";
	print "The nagios plugins come with ABSOLUTELY NO WARRANTY. You may redistribute\ncopies of the plugins under the terms of the GNU General Public License.\nFor more information about these matters, see the file named COPYING.\n";
}

sub support () {
	my $support='Send email to help@nagios-plugins.org if you have questions regarding use\nof this software. To submit patches or suggest improvements, send email to\ndevel@nagios-plugins.org. Please include version information with all\ncorrespondence (when possible, use output from the --version option of the\nplugin itself).\n';
	$support =~ s/@/\@/g;
	$support =~ s/\\n/\n/g;
	print $support;
}

sub usage {
	my $format=shift;
	printf($format,@_);
	exit $ERRORS{'UNKNOWN'};
}

sub is_hostname {
	my $host1 = shift;
	return 0 unless defined $host1;
	if ($host1 =~ m/^[\d\.]+$/ && $host1 !~ /\.$/) {
		if ($host1 =~ m/^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/) {
			return 1;
		} else {
			return 0;
		}
	} elsif ($host1 =~ m/^[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)*\.?$/) {
		return 1;
	} else {
		return 0;
	}
}

1;
