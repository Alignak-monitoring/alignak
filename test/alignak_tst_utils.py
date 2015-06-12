"""
Module (could be made a package eventually) to contain misc
little helper functions (and not having hidden side-effects or such things)
used more specifically in the tests.
"""

import locale
import socket
import sys

from sys import __stdout__


if sys.version_info[:2] < (2, 7):
    import unittest2 as unittest
    from ordereddict import OrderedDict
else:
    import unittest
    from collections import OrderedDict



def get_free_port(on_ip='127.0.0.1'):
    sock = socket.socket()
    try:
        sock.bind((on_ip, 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def guess_sys_stdout_encoding():
    ''' Return the best guessed encoding to be used for printing on sys.stdout. '''
    return (
           getattr(sys.stdout, 'encoding', None)
        or getattr(__stdout__, 'encoding', None)
        or locale.getpreferredencoding()
        or sys.getdefaultencoding()
        or 'ascii'
    )


def safe_print(*args, **kw):
    """" "print" args to sys.stdout,
    If some of the args aren't unicode then convert them first to unicode,
        using keyword argument 'in_encoding' if provided (else default to UTF8)
        and replacing bad encoded bytes.
    Write to stdout using 'out_encoding' if provided else best guessed encoding,
        doing xmlcharrefreplace on errors.
    """
    in_bytes_encoding = kw.pop('in_encoding', 'UTF-8')
    out_encoding = kw.pop('out_encoding', guess_sys_stdout_encoding())
    if kw:
        raise ValueError('unhandled named/keyword argument(s): %r' % kw)
    #
    make_in_data_gen = lambda: ( a if isinstance(a, unicode)
                                else
                            unicode(str(a), in_bytes_encoding, 'replace')
                        for a in args )

    possible_codings = ( out_encoding, )
    if out_encoding != 'ascii':
        possible_codings += ( 'ascii', )

    for coding in possible_codings:
        data = u' '.join(make_in_data_gen()).encode(coding, 'xmlcharrefreplace')
        try:
            sys.stdout.write(data)
            break
        except UnicodeError as err:
            # there might still have some problem with the underlying sys.stdout.
            # it might be a StringIO whose content could be decoded/encoded in this same process
            # and have encode/decode errors because we could have guessed a bad encoding with it.
            # in such case fallback on 'ascii'
            if coding == 'ascii':
                raise
            sys.stderr.write('Error on write to sys.stdout with %s encoding: err=%s\nTrying with ascii' % (
                coding, err))
    sys.stdout.write(b'\n')
