#!/usr/bin/env perl
# check_nginx_status.pl
# Author  : regis.leroy at makina-corpus.com
# Licence : GPL - http://www.fsf.org/licenses/gpl.txt
#
# help : ./check_nginx_status.pl -h
#
# issues & updates: http://github.com/regilero/check_nginx_status
use warnings;
use strict;
use Getopt::Long;
use LWP::UserAgent;
use Time::HiRes qw(gettimeofday tv_interval);
use Digest::MD5 qw(md5 md5_hex);
use FindBin;

# ensure all outputs are in UTF-8
binmode(STDOUT, ":utf8");

# Nagios specific
use lib $FindBin::Bin;
use utils qw($TIMEOUT);

# Globals
my $Version='0.20';
my $Name=$0;

my $o_host =          undef;  # hostname
my $o_help=           undef;  # want some help ?
my $o_port=           undef;  # port
my $o_url =           undef;  # url to use, if not the default
my $o_user=           undef;  # user for auth
my $o_pass=           '';     # password for auth
my $o_realm=          '';     # password for auth
my $o_version=        undef;  # print version
my $o_warn_a_level=   -1;     # Number of active connections that will cause a warning
my $o_crit_a_level=   -1;     # Number of active connections that will cause an error
my $o_warn_rps_level= -1;     # Number of Request per second that will cause a warning
my $o_crit_rps_level= -1;     # Number of request Per second that will cause an error
my $o_warn_cps_level= -1;     # Number of Connections per second that will cause a warning
my $o_crit_cps_level= -1;     # Number of Connections per second that will cause an error
my $o_timeout=        15;     # Default 15s Timeout
my $o_warn_thresold=  undef;  # warning thresolds entry
my $o_crit_thresold=  undef;  # critical thresolds entry
my $o_debug=          undef;  # debug mode
my $o_servername=     undef;  # ServerName (host header in http request)
my $o_https=          undef;  # SSL (HTTPS) mode
my $o_disable_sslverifyhostname = 0;

my $TempPath = '/tmp/';     # temp path
my $MaxTimeDif = 60*30;   # Maximum uptime difference (seconds), default 30 minutes

my $nginx = 'NGINX'; # Could be used to store version also

# functions
sub show_versioninfo { print "$Name version : $Version\n"; }

sub print_usage {
  print "Usage: $Name -H <host ip> [-p <port>] [-s servername] [-t <timeout>] [-w <WARN_THRESOLD> -c <CRIT_THRESOLD>] [-V] [-d] [-u <url>] [-U user -P pass -r realm]\n";
}
sub nagios_exit {
    my ( $nickname, $status, $message, $perfdata , $silent) = @_;
    my %STATUSCODE = (
      'OK' => 0
      , 'WARNING' => 1
      , 'CRITICAL' => 2
      , 'UNKNOWN' => 3
      , 'PENDING' => 4
    );
    if(!defined($silent)) {
        my $output = undef;
        $output .= sprintf('%1$s %2$s - %3$s', $nickname, $status, $message);
        if ($perfdata) {
            $output .= sprintf('|%1$s', $perfdata);
        }
        $output .= chr(10);
        print $output;
    }
    exit $STATUSCODE{$status};
}

# Get the alarm signal
$SIG{'ALRM'} = sub {
  nagios_exit($nginx,"CRITICAL","ERROR: Alarm signal (Nagios timeout)");
};

sub help {
  print "Nginx Monitor for Nagios version ",$Version,"\n";
  print "GPL licence, (c)2012 Leroy Regis\n\n";
  print_usage();
  print <<EOT;
-h, --help
   print this help message
-H, --hostname=HOST
   name or IP address of host to check
-p, --port=PORT
   Http port
-u, --url=URL
   Specific URL to use, instead of the default "http://<hostname or IP>/nginx_status"
-s, --servername=SERVERNAME
   ServerName, (host header of HTTP request) use it if you specified an IP in -H to match the good Virtualhost in your target
-S, --ssl
   Wether we should use HTTPS instead of HTTP
--disable-sslverifyhostname
   Disable SSL hostname verification
-U, --user=user
   Username for basic auth
-P, --pass=PASS
   Password for basic auth
-r, --realm=REALM
   Realm for basic auth
-d, --debug
   Debug mode (show http request response)
-m, --maxreach=MAX
   Number of max processes reached (since last check) that should trigger an alert
-t, --timeout=INTEGER
   timeout in seconds (Default: $o_timeout)
-w, --warn=ACTIVE_CONN,REQ_PER_SEC,CONN_PER_SEC
   number of active connections, ReqPerSec or ConnPerSec that will cause a WARNING
   -1 for no warning
-c, --critical=ACTIVE_CONN,REQ_PER_SEC,CONN_PER_SEC
   number of active connections, ReqPerSec or ConnPerSec that will cause a CRITICAL
   -1 for no CRITICAL
-V, --version
   prints version number

Note :
  3 items can be managed on this check, this is why -w and -c parameters are using 3 values thresolds
  - ACTIVE_CONN: Number of all opened connections, including connections to backends
  - REQ_PER_SEC: Average number of request per second between this check and the previous one
  - CONN_PER_SEC: Average number of connections per second between this check and the previous one

Examples:

  This one will generate WARNING and CRITICIAL alerts if you reach 10 000 or 20 000 active connection; or
  100 or 200 request per second; or 200 or 300 connections per second
check_nginx_status.pl -H 10.0.0.10 -u /foo/nginx_status -s mydomain.example.com -t 8 -w 10000,100,200 -c 20000,200,300

  this will generate WARNING and CRITICAL alerts only on the number of active connections (with low numbers for nginx)
check_nginx_status.pl -H 10.0.0.10 -s mydomain.example.com -t 8 -w 10,-1,-1 -c 20,-1,-1

  theses two equivalents will not generate any alert (if the nginx_status page is reachable) but could be used for graphics
check_nginx_status.pl -H 10.0.0.10 -s mydomain.example.com -w -1,-1,-1 -c -1,-1,-1
check_nginx_status.pl -H 10.0.0.10 -s mydomain.example.com

EOT
}

sub check_options {
    Getopt::Long::Configure ("bundling");
    GetOptions(
      'h'     => \$o_help,         'help'          => \$o_help,
      'd'     => \$o_debug,        'debug'         => \$o_debug,
      'H:s'   => \$o_host,         'hostname:s'    => \$o_host,
      's:s'   => \$o_servername,   'servername:s'  => \$o_servername,
      'S:s'   => \$o_https,        'ssl:s'         => \$o_https,
      'u:s'   => \$o_url,          'url:s'         => \$o_url,
      'U:s'   => \$o_user,         'user:s'        => \$o_user,
      'P:s'   => \$o_pass,         'pass:s'        => \$o_pass,
      'r:s'   => \$o_realm,        'realm:s'       => \$o_realm,
      'p:i'   => \$o_port,         'port:i'        => \$o_port,
      'V'     => \$o_version,      'version'       => \$o_version,
      'w:s'   => \$o_warn_thresold,'warn:s'        => \$o_warn_thresold,
      'c:s'   => \$o_crit_thresold,'critical:s'    => \$o_crit_thresold,
      't:i'   => \$o_timeout,      'timeout:i'     => \$o_timeout,
      'disable-sslverifyhostname' => \$o_disable_sslverifyhostname,
    );

    if (defined ($o_help)) {
        help();
        nagios_exit($nginx,"UNKNOWN","leaving","",1);
    }
    if (defined($o_version)) {
        show_versioninfo();
        nagios_exit($nginx,"UNKNOWN","leaving","",1);
    };

    if (defined($o_warn_thresold)) {
        ($o_warn_a_level,$o_warn_rps_level,$o_warn_cps_level) = split(',', $o_warn_thresold);
    }
    if (defined($o_crit_thresold)) {
        ($o_crit_a_level,$o_crit_rps_level,$o_crit_cps_level) = split(',', $o_crit_thresold);
    }
    if (defined($o_debug)) {
        print("\nDebug thresolds: \nWarning: ($o_warn_thresold) => Active: $o_warn_a_level ReqPerSec :$o_warn_rps_level ConnPerSec: $o_warn_cps_level");
        print("\nCritical ($o_crit_thresold) => : Active: $o_crit_a_level ReqPerSec: $o_crit_rps_level ConnPerSec : $o_crit_cps_level\n");
    }
    if ((defined($o_warn_a_level) && defined($o_crit_a_level)) &&
         (($o_warn_a_level != -1) && ($o_crit_a_level != -1) && ($o_warn_a_level >= $o_crit_a_level)) ) {
        nagios_exit($nginx,"UNKNOWN","Check warning and critical values for Active Process (1st part of thresold), warning level must be < crit level!");
    }
    if ((defined($o_warn_rps_level) && defined($o_crit_rps_level)) &&
         (($o_warn_rps_level != -1) && ($o_crit_rps_level != -1) && ($o_warn_rps_level >= $o_crit_rps_level)) ) {
        nagios_exit($nginx,"UNKNOWN","Check warning and critical values for ReqPerSec (2nd part of thresold), warning level must be < crit level!");
    }
    if ((defined($o_warn_cps_level) && defined($o_crit_cps_level)) &&
         (($o_warn_cps_level != -1) && ($o_crit_cps_level != -1) && ($o_warn_cps_level >= $o_crit_cps_level)) ) {
        nagios_exit($nginx,"UNKNOWN","Check warning and critical values for ConnPerSec (3rd part of thresold), warning level must be < crit level!");
    }
    # Check compulsory attributes
    if (!defined($o_host)) {
        print_usage();
        nagios_exit($nginx,"UNKNOWN","-H host argument required");
    }
}

########## MAIN ##########

check_options();

my $override_ip = $o_host;
my $ua = LWP::UserAgent->new(
  protocols_allowed => ['http', 'https'],
  timeout => $o_timeout
);

if ( $o_disable_sslverifyhostname ) {
  $ua->ssl_opts( 'verify_hostname' => 0 );
}

# we need to enforce the HTTP request is made on the Nagios Host IP and
# not on the DNS related IP for that domain
@LWP::Protocol::http::EXTRA_SOCK_OPTS = ( PeerAddr => $override_ip );
# this prevent used only once warning in -w mode
my $ua_settings = @LWP::Protocol::http::EXTRA_SOCK_OPTS;

my $timing0 = [gettimeofday];
my $response = undef;
my $url = undef;

if (!defined($o_url)) {
    $o_url='/nginx_status';
} else {
    # ensure we have a '/' as first char
    $o_url = '/'.$o_url unless $o_url =~ m(^/)
}
my $proto='http://';
if(defined($o_https)) {
    $proto='https://';
    if (defined($o_port) && $o_port!=443) {
        if (defined ($o_debug)) {
            print "\nDEBUG: Notice: port is defined at $o_port and not 443, check you really want that in SSL mode! \n";
        }
    }
}
if (defined($o_servername)) {
    if (!defined($o_port)) {
        $url = $proto . $o_servername . $o_url;
    } else {
        $url = $proto . $o_servername . ':' . $o_port . $o_url;
    }
} else {
    if (!defined($o_port)) {
        $url = $proto . $o_host . $o_url;
    } else {
        $url = $proto . $o_host . ':' . $o_port . $o_url;
    }
}
if (defined ($o_debug)) {
    print "\nDEBUG: HTTP url: \n";
    print $url;
}

my $req = HTTP::Request->new( GET => $url );

if (defined($o_servername)) {
    $req->header('Host' => $o_servername);
}
if (defined($o_user)) {
    $req->authorization_basic($o_user, $o_pass);
}

if (defined ($o_debug)) {
    print "\nDEBUG: HTTP request: \n";
    print "IP used (better if it's an IP):" . $override_ip . "\n";
    print $req->as_string;
}
$response = $ua->request($req);
my $timeelapsed = tv_interval ($timing0, [gettimeofday]);

my $InfoData = '';
my $PerfData = '';
#my @Time = (localtime); # list context and not scalar as we want the brutal timestamp
my $Time = time;

my $webcontent = undef;
if ($response->is_success) {
    $webcontent=$response->decoded_content;
    if (defined ($o_debug)) {
        print "\nDEBUG: HTTP response:";
        print $response->status_line;
        print "\n".$response->header('Content-Type');
        print "\n";
        print $webcontent;
    }
    if ($response->header('Content-Type') =~ m/text\/html/) {
        nagios_exit($nginx,"CRITICAL", "We have a response page for our request, but it's an HTML page, quite certainly not the status report of nginx");
    }
    # example of response content expected:
    #Active connections: 10
    #server accepts handled requests
    #38500 38500 50690
    #Reading: 5 Writing: 5 Waiting: 0

    # number of all open connections including connections to backends
    my $ActiveConn = 0;
    if($webcontent =~ m/Active connections: (.*?)\n/) {
        $ActiveConn = $1;
        # triming
        $ActiveConn =~ s/^\s+|\s+$//g;
    }


    # 3 counters with a space: accepted conn, handled conn and number of requests
    my $counters = '';
    my $AcceptedConn = 0;
    my $HandledConn = 0;
    my $NbRequests = 0;
    if($webcontent =~ m/\nserver accepts handled requests\n(.*?)\n/) {
        $counters = $1;
        # triming
        $counters =~ s/^\s+|\s+$//g;
        #splitting
        ($AcceptedConn,$HandledConn,$NbRequests) = split(' ', $counters);
        # triming
        $AcceptedConn =~ s/^\s+|\s+$//g;
        $HandledConn =~ s/^\s+|\s+$//g;
        $NbRequests =~ s/^\s+|\s+$//g;
    }

    # nginx reads request header
    my $Reading = 0;
    # nginx reads request body, processes request, or writes response to a client
    my $Writing = 0;
    # keep-alive connections, actually it is active - (reading + writing)
    my $Waiting = 0;
    if($webcontent =~ m/Reading: (.*?)Writing: (.*?)Waiting: (.*?)$/) {
        $Reading = $1;
        $Writing = $2;
        $Waiting = $3;
        # triming
        $Reading =~ s/^\s+|\s+$//g;
        $Writing =~ s/^\s+|\s+$//g;
        $Waiting =~ s/^\s+|\s+$//g;
    }

    # Debug
    if (defined ($o_debug)) {
        print ("\nDEBUG Parse results => Active :" . $ActiveConn . "\nAcceptedConn :" . $AcceptedConn . "\nHandledConn :" . $HandledConn . "\nNbRequests :".$NbRequests . "\nReading :" .$Reading . "\nWriting :" . $Writing . "\nWaiting :" . $Waiting . "\n");
    }

    my $TempFile = $TempPath.$o_host.'_check_nginx_status'.md5_hex($url);
    my $FH;

    my $LastTime = 0;
    my $LastAcceptedConn = 0;
    my $LastHandledConn = 0;
    my $LastNbRequests = 0;
    if ((-e $TempFile) && (-r $TempFile) && (-w $TempFile)) {
        open ($FH, '<',$TempFile) or nagios_exit($nginx,"UNKNOWN","unable to read temporary data from :".$TempFile);
        $LastTime = <$FH>;
        $LastAcceptedConn = <$FH>;
        $LastHandledConn = <$FH>;
        $LastNbRequests = <$FH>;
        close ($FH);
        if (defined ($o_debug)) {
            print ("\nDebug: data from temporary file: $TempFile\n");
            print (" LastTime: $LastTime LastAcceptedConn: $LastAcceptedConn LastHandledConn: $LastHandledConn LastNbRequests: $LastNbRequests \n");
        }
    }

    open ($FH, '>'.$TempFile) or nagios_exit($nginx,"UNKNOWN","unable to write temporary data in :".$TempFile);
    #print $FH (@Time),"\n";
    print $FH "$Time\n";
    print $FH "$AcceptedConn\n";
    print $FH "$HandledConn\n";
    print $FH "$NbRequests\n";
    close ($FH);

    my $ConnPerSec = 0;
    my $ReqPerSec = 0;
    my $RequestsNew = 0;
    # by default the average
    my $ReqPerConn = 0;
    if ($AcceptedConn > 0) {
        $ReqPerConn = $NbRequests/$AcceptedConn;
    }
    my $elapsed = $Time  - $LastTime ;
    if (defined ($o_debug)) {
        print ("\nDebug: pre-computation\n");
        print ("Average ReqPerconn: $ReqPerConn, Seconds elapsed Since last check: $elapsed\n");
    }
    # check only if the counters may have been incremented
    # but not if it may have been too much incremented
    # if nginx was restarted ($NbRequests is now lower than previous value), just skip
    if ( ($elapsed < $MaxTimeDif) && ($elapsed != 0) && ($NbRequests >= $LastNbRequests) ) {
        $ConnPerSec = ($AcceptedConn-$LastAcceptedConn)/$elapsed;
        $RequestsNew = $NbRequests-$LastNbRequests;
        $ReqPerSec = $RequestsNew/$elapsed;
        # get finer value
        if ( $ConnPerSec!=0 ) {
          my $ReqPerConn = $ReqPerSec/$ConnPerSec;
        } else {
          my $ReqPerConn = 0;
        }
    }
    if (defined ($o_debug)) {
        print ("\nDebug: data computed\n");
        print ("ConnPerSec: $ConnPerSec ReqPerSec: $ReqPerSec ReqPerConn: $ReqPerConn\n");
    }
    $InfoData = sprintf (" %.3f sec. response time, Active: %d (Writing: %d Reading: %d Waiting: %d)"
                 . " ReqPerSec: %.3f ConnPerSec: %.3f ReqPerConn: %.3f"
                 ,$timeelapsed,$ActiveConn,$Writing,$Reading,$Waiting,$ReqPerSec,$ConnPerSec,$ReqPerConn);
                 
    # Manage warn and crit values for the perfdata
	 my $p_warn_a_level = "$o_warn_a_level";
	 my $p_crit_a_level = "$o_crit_a_level";
	 my $p_warn_rps_level = "$o_warn_rps_level";
	 my $p_crit_rps_level = "$o_crit_rps_level";
	 my $p_warn_cps_level = "$o_warn_cps_level";
	 my $p_crit_cps_level = "$o_crit_cps_level";             

	 if ($p_warn_a_level == "-1") {
	     $p_warn_a_level = "";
	 }
	 if ($p_crit_a_level == "-1") {
	     $p_crit_a_level = "";
	 }
	 if ($p_warn_rps_level == "-1") {
	     $p_warn_rps_level = "";
	 }
	 if ($p_crit_rps_level == "-1") {
	     $p_crit_rps_level = "";
	 }
	 if ($p_warn_cps_level == "-1") {
	     $p_warn_cps_level = "";
	 }
	 if ($p_crit_cps_level == "-1") {
	     $p_crit_cps_level = "";
	 }
                 
    $PerfData = sprintf ("Writing=%d;;;; Reading=%d;;;; Waiting=%d;;;; Active=%d;%s;%s;; "
                 . "ReqPerSec=%f;%s;%s;; ConnPerSec=%f;%s;%s;; ReqPerConn=%f;;;;"
                 ,($Writing),($Reading),($Waiting),($ActiveConn)
                 ,($p_warn_a_level),($p_crit_a_level)
                 ,($ReqPerSec),($p_warn_rps_level),($p_crit_rps_level)
                 ,($ConnPerSec),($p_warn_cps_level),($p_crit_cps_level)
                 ,($ReqPerConn));
    # first all critical exists by priority
    if (defined($o_crit_a_level) && (-1!=$o_crit_a_level) && ($ActiveConn >= $o_crit_a_level)) {
        nagios_exit($nginx,"CRITICAL", "Active Connections are critically high " . $InfoData,$PerfData);
    }
    if (defined($o_crit_rps_level) && (-1!=$o_crit_rps_level) && ($ReqPerSec >= $o_crit_rps_level)) {
        nagios_exit($nginx,"CRITICAL", "Request per second ratios is critically high " . $InfoData,$PerfData);
    }
    if (defined($o_crit_cps_level) && (-1!=$o_crit_cps_level) && ($ConnPerSec >= $o_crit_cps_level)) {
        nagios_exit($nginx,"CRITICAL", "Connection per second ratio is critically high " . $InfoData,$PerfData);
    }
    # Then WARNING exits by priority
    if (defined($o_warn_a_level) && (-1!=$o_warn_a_level) && ($ActiveConn >= $o_warn_a_level)) {
        nagios_exit($nginx,"WARNING", "Active Connections are high " . $InfoData,$PerfData);
    }
    if (defined($o_warn_rps_level) && (-1!=$o_warn_rps_level) && ($ReqPerSec >= $o_warn_rps_level)) {
        nagios_exit($nginx,"WARNING", "Requests per second ratio is high " . $InfoData,$PerfData);
    }
    if (defined($o_warn_cps_level) && (-1!=$o_warn_cps_level) && ($ConnPerSec >= $o_warn_cps_level)) {
        nagios_exit($nginx,"WARNING", "Connection per second ratio is high " . $InfoData,$PerfData);
    }

    nagios_exit($nginx,"OK",$InfoData,$PerfData);

} else {
    nagios_exit($nginx,"CRITICAL", $response->status_line);
}
