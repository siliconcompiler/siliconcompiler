'''
LOOK FOR THIS TEXT IN HELP
'''
import sys
from siliconcompiler.apps import smake


def asic():
    print("ASIC MAKE DECORATED")


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


if __name__ == "__main__":
    sys.exit(smake.main(__file__))
