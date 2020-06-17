import logging
import os

import mock
import pytest

from nutcli.shell import Shell, ShellCommandError, ShellEnvironment, ShellResult, ShellTimeoutError


def test_ShellEnvironment_defaults__system():
    os_env = os.environ
    env = ShellEnvironment(clear_env=False)
    assert env.default == os_env


def test_ShellEnvironment_defaults__clear():
    env = ShellEnvironment(clear_env=True)
    assert not env.default


def test_ShellEnvironment_overrides__system():
    os_env = os.environ
    env = ShellEnvironment()
    overrides = {'KEY': 'VALUE'}
    returned = env.set(overrides)

    assert env.overrides == overrides
    assert env == returned
    assert env.get_overrides() == overrides
    assert env.get() == {**os_env, **overrides}


def test_ShellEnvironment_overrides__clear():
    env = ShellEnvironment(clear_env=True)
    overrides = {'KEY': 'VALUE'}
    returned = env.set(overrides)

    assert env.overrides == overrides
    assert env == returned
    assert env.get_overrides() == overrides
    assert env.get() == overrides


def test_Shell__success():
    shell = Shell()
    result = shell('exit 0')

    assert result.rc == 0
    assert result.stdout is None
    assert result.stderr is None


def test_Shell__success_list():
    shell = Shell()
    result = shell(['/bin/bash', '-c', 'exit 0'])

    assert result.rc == 0
    assert result.stdout is None
    assert result.stderr is None


def test_Shell__success_capture_stdout():
    shell = Shell()
    result = shell('echo -n hello', capture_output=True)

    assert result.rc == 0
    assert result.stdout == 'hello'
    assert result.stderr == ''


def test_Shell__success_capture_stderr():
    shell = Shell()
    result = shell('echo -n hello 1>&2', capture_output=True)

    assert result.rc == 0
    assert result.stdout == ''
    assert result.stderr == 'hello'


def test_Shell__success_capture_stdout_and_stderr():
    shell = Shell()
    result = shell('echo -n hello; echo -n world 1>&2', capture_output=True)

    assert result.rc == 0
    assert result.stdout == 'hello'
    assert result.stderr == 'world'


def test_Shell__success_capture_stdout_binary():
    shell = Shell()
    result = shell('echo -n hello', capture_output=True, text=False)

    assert result.rc == 0
    assert result.stdout.decode('utf-8') == 'hello'
    assert result.stderr.decode('utf-8') == ''


def test_Shell__success_capture_stderr_binary():
    shell = Shell()
    result = shell('echo -n hello 1>&2', capture_output=True, text=False)

    assert result.rc == 0
    assert result.stdout.decode('utf-8') == ''
    assert result.stderr.decode('utf-8') == 'hello'


def test_Shell__success_capture_stdout_and_stderr_binary():
    shell = Shell()
    result = shell('echo -n hello; echo -n world 1>&2', capture_output=True, text=False)

    assert result.rc == 0
    assert result.stdout.decode('utf-8') == 'hello'
    assert result.stderr.decode('utf-8') == 'world'


def test_Shell__success_env():
    shell = Shell(env={'KEY': 'VALUE'})

    result = shell('echo -n $KEY', capture_output=True)
    assert result.rc == 0
    assert result.stdout == 'VALUE'
    assert result.stderr == ''

    result = shell('echo -n $KEY', env={'KEY': 'NONE'}, capture_output=True)
    assert result.rc == 0
    assert result.stdout == 'NONE'
    assert result.stderr == ''


def test_Shell__success_cwd():
    shell = Shell(cwd='/')

    result = shell('echo -n `pwd`', capture_output=True)
    assert result.rc == 0
    assert result.stdout == '/'
    assert result.stderr == ''

    result = shell('echo -n `pwd`', cwd='/tmp', capture_output=True)
    assert result.rc == 0
    assert result.stdout == '/tmp'
    assert result.stderr == ''


def test_Shell__success_shell():
    shell = Shell(shell=['/bin/bash', '-c'])
    result = shell('echo -n $0', capture_output=True)
    assert result.rc == 0
    assert result.stdout == '/bin/bash'
    assert result.stderr == ''

    shell = Shell(shell=['/bin/zsh', '-c'])
    result = shell('echo -n $0', capture_output=True)
    assert result.rc == 0
    assert result.stdout == '/bin/zsh'
    assert result.stderr == ''


def test_Shell__failure_nocheck():
    shell = Shell()
    result = shell('exit 1', check=False)

    assert result.rc == 1
    assert result.stdout is None
    assert result.stderr is None


def test_Shell__failure_check():
    shell = Shell()

    with pytest.raises(ShellCommandError) as e:
        assert shell('exit 1')

    assert e.value.rc == 1
    assert e.value.cmd == 'exit 1'
    assert e.value.cwd == os.getcwd()
    assert e.value.env is not None and isinstance(e.value.env, ShellEnvironment)
    assert e.value.stdout is None
    assert e.value.stderr is None


def test_Shell__failure_timeout():
    shell = Shell()

    with pytest.raises(ShellTimeoutError) as e:
        assert shell('sleep 2', timeout=1)

    assert e.value.timeout == 1
    assert e.value.cmd == 'sleep 2'
    assert e.value.cwd == os.getcwd()
    assert e.value.env is not None and isinstance(e.value.env, ShellEnvironment)
    assert e.value.stdout is None
    assert e.value.stderr is None


@mock.patch(
    'nutcli.decorators.LogExecution.should_log_execution',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_Shell__log_execution(_, caplog):
    shell = Shell()

    with caplog.at_level(logging.DEBUG):
        shell('exit 0', effect=shell.Effect.LogExecution)
    assert 'exit 0' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        shell('exit 0', effect=shell.Effect.LogExecution, execution_message='TEST')
    assert 'TEST' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        shell('exit 0', effect=shell.Effect.Blank)
    assert not caplog.text
    caplog.clear()


@mock.patch(
    'nutcli.decorators.SideEffect.is_dry_run',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_Shell__side_effect(_, caplog):
    shell = Shell()

    with caplog.at_level(logging.DEBUG):
        result = shell('exit 0', effect=shell.Effect.SideEffect)
    assert isinstance(result, ShellResult) and result.rc == 0
    assert 'exit 0' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        result = shell('exit 0', effect=shell.Effect.SideEffect, execution_message='TEST')
    assert isinstance(result, ShellResult) and result.rc == 0
    assert 'TEST' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        result = shell('exit 0', effect=shell.Effect.SideEffect, dry_run_result=ShellResult(1, 'OUT', 'ERR'))
    assert isinstance(result, ShellResult)
    assert result.rc == 1
    assert result.stdout == 'OUT'
    assert result.stderr == 'ERR'
    assert 'exit 0' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        result = shell('exit 0', effect=shell.Effect.Blank)
    assert isinstance(result, ShellResult) and result.rc == 0
    assert not caplog.text
    caplog.clear()


@mock.patch(
    'nutcli.decorators.LogExecution.should_log_execution',
    new_callable=mock.PropertyMock,
    return_value=True
)
@mock.patch(
    'nutcli.decorators.SideEffect.is_dry_run',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_Shell__default_effect(_a, _b, caplog):
    shell = Shell(default_effect=Shell.Effect.Blank)
    with caplog.at_level(logging.DEBUG):
        result = shell('exit 0', dry_run_result=ShellResult(1))
    assert result.rc == 0
    assert not caplog.text
    caplog.clear()

    shell = Shell(default_effect=Shell.Effect.LogExecution)
    with caplog.at_level(logging.DEBUG):
        result = shell('exit 0', dry_run_result=ShellResult(1))
    assert result.rc == 0
    assert 'exit 0' in caplog.text
    caplog.clear()

    shell = Shell(default_effect=Shell.Effect.SideEffect)
    with caplog.at_level(logging.DEBUG):
        result = shell('exit 0', dry_run_result=ShellResult(1))
    assert result.rc == 1
    assert 'exit 0' in caplog.text
    caplog.clear()
