'''alignak.receiverlink is deprecated. Please use alignak.objects.receiverlink now.'''

from alignak.old_daemon_link import make_deprecated_daemon_link

from alignak.objects import receiverlink

make_deprecated_daemon_link(receiverlink)
