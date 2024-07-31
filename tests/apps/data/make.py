'''
LOOK FOR THIS TEXT IN HELP
'''

__scdefault = 'lint'


def asic():
    print("ASIC MAKE")


def lint():
    '''
    LINT HELP
    '''
    print("LINT MAKE")


def has_arg(target: str):
    print("target", target)


def has_arg2(target: str, count: int):
    assert isinstance(count, int)
    print("target", target, count)
