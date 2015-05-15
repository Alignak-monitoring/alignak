'''alignak.satellitelink is deprecated. Please use alignak.objects.satellitelink now.'''

from alignak.old_daemon_link import deprecation, make_deprecated

deprecation(__doc__)

from alignak.objects.satellitelink import (
    SatelliteLink,
    SatelliteLinks,
)

SatelliteLink = make_deprecated(SatelliteLink)
SatelliteLinks = make_deprecated(SatelliteLinks)
