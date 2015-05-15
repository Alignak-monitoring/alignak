'''alignak.pollerlink is deprecated. Please use alignak.objects.pollerlink now.'''

from alignak.old_daemon_link import make_deprecated_daemon_link

from alignak.objects import pollerlink

make_deprecated_daemon_link(pollerlink)
