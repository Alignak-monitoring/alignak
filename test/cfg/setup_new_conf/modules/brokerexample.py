from alignak.basemodule import BaseModule
from alignak.log import logger

properties = {
    # Which daemon can load this module
    'daemons': ['broker'],
    # name of the module type ; to distinguish between them:
    'type': 'example',
     # is the module "external" (external means here a daemon module)
    'external': True,
    # Possible configuration phases where the module is involved:
    'phases': ['configuration', 'late_configuration', 'running', 'retention'],
}


def get_instance(mod_conf):
    logger.info("[brokerexample] Example module %s",
                mod_conf.get_name())
    instance = Brokerexample(mod_conf)
    return instance


class Brokerexample(BaseModule):
    def __init__(self, modconf):
        BaseModule.__init__(self, modconf)

    def init(self):
        logger.info("[Dummy Broker] Initialization of the dummy broker module")
        pass
