import logging
import datetime
import shutil
import inspect

import pytest
from _pytest.config import Config
from _pytest.python import Function



@pytest.hookimpl
def pytest_configure(config: Config):
    logging.getLogger('Tester').debug(f'{"-"*20} init {"-"*20}')

    config.addinivalue_line('markers', 'login: requires user login info')


@pytest.hookimpl
def pytest_unconfigure(config: Config):
    logging.getLogger('Tester').debug(f'{"-"*20} end {"-"*20}')

    timestamp = datetime.datetime.strftime(datetime.datetime.now(), '%Y_%m_%d_%H_%M_%S')
    shutil.copyfile('logs/pytest/pytest.log', f'logs/pytest/pytest_{timestamp}.log')


@pytest.hookimpl
def pytest_runtest_setup(item: pytest.Item):
    logging.getLogger('Tester').debug(f'{item.parent.name}::{item.name}')
    logging.getLogger('Tester').debug(f'{"-"*20} setup {"-"*20}')


@pytest.hookimpl
def pytest_pyfunc_call(pyfuncitem):
    logging.getLogger('Tester').debug(f'{"-"*20} start {"-"*20}')


@pytest.hookimpl
def pytest_runtest_teardown(item: pytest.Item):
    logging.getLogger('Tester').debug(f'{"-"*20} clean {"-"*20}')
