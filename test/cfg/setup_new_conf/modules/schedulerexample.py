from alignak.basemodule import BaseModule
from alignak.log import logger

properties = {
    # Which daemon can load this module
    'daemons': ['scheduler'],
    # name of the module type ; to distinguish between them:
    'type': 'example',
     # is the module "external" (external means here a daemon module)
    'external': True,
    # Possible configuration phases where the module is involved:
    'phases': ['configuration', 'late_configuration', 'running', 'retention'],
}


def get_instance(mod_conf):
    logger.info("[schedulerexample] Example module %s",
                mod_conf.get_name())
    instance = Schedulerexample(mod_conf)
    return instance


class Schedulerexample(BaseModule):
    def __init__(self, modconf):
        BaseModule.__init__(self, modconf)

    def init(self):
        logger.info("[Dummy Scheduler] Initialization of the dummy scheduler module")
        pass
