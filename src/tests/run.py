"""
To be run from `./src` directory
"""
# noqa
# flake8: noqa
import os
import sys
import pytest



sys.path.append(os.getcwd())


if __name__ == '__main__':
    # NOTE: `maxfail=2` allows pytest-check to fail mutliple times where `with pytest_check.check:` is used
    args = [ '--tb=short', '--showlocals', '--maxfail=2', '-rA', f'{os.getcwd()}\\src\\tests\\unit_tests' ]
    for arg in sys.argv:
        # append addition args from command line
        # ex: `python tests\run.py -k test_forum_driver`
        args.append(arg)

    ret = pytest.main(args)
    input('Hit enter to exit...')
    sys.exit(ret)

