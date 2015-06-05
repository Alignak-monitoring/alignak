
from types import ModuleType

class CustomModule(ModuleType):
    """Custom module that can be used to customize a module namespace,

    example usage:

    >>> import sys
    >>> assert __name__ == 'custom_module'  # required for the import after
    >>> class MyCustomModule(CustomModule):
    ...     count = 0
    ...     @property
    ...     def an_attribute(self):
    ...         self.count += 1
    ...         return "hey ! I'm a module attribute but also a property !"
    >>> sys.modules[__name__] = MyCustomModule(__name__, globals())

    # then, in another module:
    >>> import custom_module
    >>> assert custom_module.count == 0
    >>> custom_module.an_attribute
    "hey ! I'm a module attribute but also a property !"
    >>> assert custom_module.count == 1
    """

    def __init__(self, name, orig_mod_globals):
        super(CustomModule, self).__init__(name)
        self.__dict__.update(**orig_mod_globals)
