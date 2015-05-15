'''alignak.brokerlink is deprecated. Please use alignak.objects.brokerlink now.'''

from alignak.old_daemon_link import make_deprecated_daemon_link

from alignak.objects import brokerlink

make_deprecated_daemon_link(brokerlink)
