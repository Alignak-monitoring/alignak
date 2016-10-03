from alignak.basemodule import BaseModule
from alignak.log import logger

properties = {
    # Which daemon can load this module
    'daemons': ['receiver'],
    # name of the module type ; to distinguish between them:
    'type': 'example',
     # is the module "external" (external means here a daemon module)
    'external': True,
    # Possible configuration phases where the module is involved:
    'phases': ['configuration', 'late_configuration', 'running', 'retention'],
}


def get_instance(mod_conf):
    logger.info("[receiverexample] Example module %s",
                mod_conf.get_name())
    instance = Receiverexample(mod_conf)
    return instance


class Receiverexample(BaseModule):
    def __init__(self, modconf):
        BaseModule.__init__(self, modconf)

    def init(self):
        logger.info("[Dummy Receiver] Initialization of the dummy receiver module")
        pass
