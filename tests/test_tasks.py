import logging
import mock
import time

import pytest

from nutcli.exceptions import TimeoutError
from nutcli.tasks import *


def test_Task__disabled(caplog):
    task = Task('Test', enabled=False)(lambda: logging.info('HELLO'))
    with caplog.at_level(logging.DEBUG):
        task.execute()
    assert not caplog.text


def test_Task__taskarg(caplog):
    task = Task('Test')(lambda: logging.info('HELLO'))
    with caplog.at_level(logging.DEBUG):
        task.execute()
    assert 'HELLO' in caplog.text
    caplog.clear()

    task = Task('Test')(lambda task: logging.info('HELLO'))
    with caplog.at_level(logging.DEBUG):
        task.execute()
    assert 'HELLO' in caplog.text
    caplog.clear()

    t1 = Task('Test')
    def test_fn(task):
        assert task == t1
    t1(test_fn)
    t1.execute()

    t2 = Task('Test')
    def test_fn2(task):
        assert task == 'test'
    t2(test_fn2, 'test')
    t2.execute()

    t3 = Task('Test')
    def test_fn3(task):
        assert task == 'kwtest'
    t3(test_fn3, task='kwtest')
    t3.execute()


def test_Task__ignore_errors(caplog):
    def fn():
        raise Exception()

    task = Task('Test', ignore_errors=False)(fn)
    with pytest.raises(Exception):
        task.execute()

    task = Task('Test', ignore_errors=True)(fn)
    task.execute()


def test_Task__timeout(caplog):
    def fn():
        time.sleep(2)

    task = Task('Test', timeout=1)(fn)
    with pytest.raises(TimeoutError) as e:
        task.execute()
    assert e.value.timeout == 1

    task = Task('Test', timeout='1 second')(fn)
    with pytest.raises(TimeoutError) as e:
        task.execute()
    assert e.value.timeout == 1


def test_Task__override_ignore_errors(caplog):
    def fn():
        raise Exception()

    task = Task('Test', ignore_errors=True)(fn)
    with pytest.raises(Exception):
        task.execute(ignore_errors=False)

    task = Task('Test', ignore_errors=False)(fn)
    task.execute(ignore_errors=True)


def test_Task__override_timeout(caplog):
    def fn():
        time.sleep(2)

    task = Task('Test', timeout=None)(fn)
    with pytest.raises(TimeoutError) as e:
        task.execute(timeout=1)
    assert e.value.timeout == 1

    task = Task('Test', timeout=None)(fn)
    with pytest.raises(TimeoutError) as e:
        task.execute(timeout='1 second')
    assert e.value.timeout == 1


def test_Task_Cleanup():
    task = Task.Cleanup()
    assert task.ignore_errors is True
    assert task.always is True


def test_Task__messages(caplog):
    task = Task('Test',)(lambda task: task.debug('HELLO'))
    with caplog.at_level(logging.DEBUG):
        task.execute()
    assert 'DEBUG' in caplog.text
    assert 'HELLO' in caplog.text
    caplog.clear()

    task = Task('Test')(lambda task: task.info('HELLO'))
    with caplog.at_level(logging.DEBUG):
        task.execute()
    assert 'INFO' in caplog.text
    assert 'HELLO' in caplog.text
    caplog.clear()

    task = Task('Test')(lambda task: task.warning('HELLO'))
    with caplog.at_level(logging.DEBUG):
        task.execute()
    assert 'WARNING' in caplog.text
    assert 'HELLO' in caplog.text
    caplog.clear()

    task = Task('Test')(lambda task: task.error('HELLO'))
    with caplog.at_level(logging.DEBUG):
        task.execute()
    assert 'ERROR' in caplog.text
    assert 'HELLO' in caplog.text
    caplog.clear()

    task = Task('Test')(lambda task: task.critical('HELLO'))
    with caplog.at_level(logging.DEBUG):
        task.execute()
    assert 'CRITICAL' in caplog.text
    assert 'HELLO' in caplog.text
    caplog.clear()


def test_TaskList__basic(caplog):
    tasklist = TaskList()([
        Task('Task 1')(lambda task: task.info('T1'))
    ])

    with caplog.at_level(logging.DEBUG):
        tasklist.execute()
    assert '[1/1] Task 1' in caplog.text
    assert 'T1' in caplog.text

    tasklist = TaskList()([
        Task('Task 1')(lambda task: task.info('T1')),
        Task('Task 2')(lambda task: task.info('T2'))
    ])

    with caplog.at_level(logging.DEBUG):
        tasklist.execute()
    assert '[1/2] Task 1' in caplog.text
    assert '[2/2] Task 2' in caplog.text
    assert 'T1' in caplog.text
    assert 'T2' in caplog.text


def test_TaskList__tag(caplog):
    tasklist = TaskList('TEST')([
        Task('Task 1')(lambda task: task.info('T1'))
    ])

    with caplog.at_level(logging.DEBUG):
        tasklist.execute()
    assert '[TEST] [1/1] Task 1' in caplog.text
    assert 'T1' in caplog.text


def test_TaskList__always_false(caplog):
    def task_raise(task):
        raise Exception()

    tasklist = TaskList()([
        Task('Task 1', always=False)(task_raise),
        Task('Task 2', always=False)(lambda task: task.info('T2'))
    ])

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(Exception):
            tasklist.execute()

    assert '[1/2] Task 1' in caplog.text
    assert '[2/2] Task 2 (skipped on error)' in caplog.text
    assert 'T2' not in caplog.text


def test_TaskList__always_true(caplog):
    def task_raise(task):
        raise Exception()

    tasklist = TaskList()([
        Task('Task 1', always=False)(task_raise),
        Task('Task 2', always=True)(lambda task: task.info('T2'))
    ])

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(Exception):
            tasklist.execute()

    assert '[1/2] Task 1' in caplog.text
    assert '[2/2] Task 2 (finalizing)' in caplog.text
    assert 'T2' in caplog.text


def test_TaskList__messages(caplog):
    tasklist = TaskList('TEST')([
        Task('Task 1')(lambda task: task.debug('T1'))
    ])
    with caplog.at_level(logging.DEBUG):
        tasklist.execute()
    assert 'DEBUG' in caplog.text
    assert '[TEST] [1/1] Task 1'
    assert '[TEST]   T1' in caplog.text
    caplog.clear()

    tasklist = TaskList('TEST')([
        Task('Task 1')(lambda task: task.info('T1'))
    ])
    with caplog.at_level(logging.DEBUG):
        tasklist.execute()
    assert 'INFO' in caplog.text
    assert '[TEST] [1/1] Task 1'
    assert '[TEST]   T1' in caplog.text
    caplog.clear()

    tasklist = TaskList('TEST')([
        Task('Task 1')(lambda task: task.warning('T1'))
    ])
    with caplog.at_level(logging.DEBUG):
        tasklist.execute()
    assert 'WARNING' in caplog.text
    assert '[TEST] [1/1] Task 1'
    assert '[TEST]   T1' in caplog.text
    caplog.clear()

    tasklist = TaskList('TEST')([
        Task('Task 1')(lambda task: task.error('T1'))
    ])
    with caplog.at_level(logging.DEBUG):
        tasklist.execute()
    assert 'ERROR' in caplog.text
    assert '[TEST] [1/1] Task 1'
    assert '[TEST]   T1' in caplog.text
    caplog.clear()

    tasklist = TaskList('TEST')([
        Task('Task 1')(lambda task: task.critical('T1'))
    ])
    with caplog.at_level(logging.DEBUG):
        tasklist.execute()
    assert 'CRITICAL' in caplog.text
    assert '[TEST] [1/1] Task 1'
    assert '[TEST]   T1' in caplog.text
    caplog.clear()


def test_TaskList__nested(caplog):
    tasklist = TaskList('L1')([
        Task('Task 1')(lambda task: task.info('T1')),
        TaskList('L2')([
            Task('Task 2', always=True)(lambda task: task.info('T2'))
        ])
    ])

    with caplog.at_level(logging.DEBUG):
        tasklist.execute()

    assert '[L1] [1/2] Task 1' in caplog.text
    assert 'T1' in caplog.text
    assert '[L1] [2/2]' in caplog.text
    assert '[L1]   [L2] [1/1] Task 2' in caplog.text
    assert 'T2' in caplog.text


def test_TaskList__nested_name(caplog):
    tasklist = TaskList('L1')([
        Task('Task 1')(lambda task: task.info('T1')),
        TaskList('L2', 'TaskList2')([
            Task('Task 2', always=True)(lambda task: task.info('T2'))
        ])
    ])

    with caplog.at_level(logging.DEBUG):
        tasklist.execute()

    assert '[L1] [1/2] Task 1' in caplog.text
    assert 'T1' in caplog.text
    assert '[L1] [2/2] TaskList2' in caplog.text
    assert '[L1]   [L2] [1/1] Task 2' in caplog.text
    assert 'T2' in caplog.text


def test_TaskList__disabled_tasks_basic(caplog):
    def task_disabled(task):
        assert False

    tasklist = TaskList('L1')([
        Task('Task 1', enabled=False)(task_disabled),
    ])

    with caplog.at_level(logging.DEBUG):
        tasklist.execute()

    assert not caplog.text

def test_TaskList__disabled_tasks_complex(caplog):
    def task_disabled(task):
        assert False

    tasklist = TaskList('L1')([
        Task('Task 1', enabled=False)(task_disabled),
        Task('Task 2', enabled=True)(lambda task: task.info('T2')),
    ])

    with caplog.at_level(logging.DEBUG):
        tasklist.execute()

    assert '[L1] [1/1] Task 2' in caplog.text


def test_TaskList__list_methods(caplog):
    tasklist = TaskList()
    t1 = Task()
    t2 = Task()
    t3 = Task()

    assert not tasklist.tasks
    assert len(tasklist) == 0
    assert t1 not in tasklist
    assert t2 not in tasklist
    assert t3 not in tasklist

    tasklist.append(t1)
    assert tasklist.tasks == [t1]
    assert len(tasklist) == 1
    assert tasklist[0] == t1
    assert t1 in tasklist
    assert t2 not in tasklist
    assert t3 not in tasklist

    tasklist.extend([t2])
    assert tasklist.tasks == [t1, t2]
    assert len(tasklist) == 2
    assert tasklist[0] == t1
    assert tasklist[1] == t2
    assert t1 in tasklist
    assert t2 in tasklist
    assert t3 not in tasklist

    tasklist.insert(1, t3)
    assert tasklist.tasks == [t1, t3, t2]
    assert len(tasklist) == 3
    assert tasklist[0] == t1
    assert tasklist[1] == t3
    assert tasklist[2] == t2
    assert t1 in tasklist
    assert t2 in tasklist
    assert t3 in tasklist

    tasklist.remove(t3)
    assert tasklist.tasks == [t1, t2]
    assert len(tasklist) == 2
    assert tasklist[0] == t1
    assert tasklist[1] == t2
    assert t1 in tasklist
    assert t2 in tasklist
    assert t3 not in tasklist

    tasklist.pop()
    assert tasklist.tasks == [t1]
    assert len(tasklist) == 1
    assert tasklist[0] == t1
    assert t1 in tasklist
    assert t2 not in tasklist
    assert t3 not in tasklist

    tasklist.clear()
    assert not tasklist.tasks
    assert len(tasklist) == 0
    assert t1 not in tasklist
    assert t2 not in tasklist
    assert t3 not in tasklist

    tasklist.tasks = [None]
    tasklist[0] = t1
    assert tasklist.tasks == [t1]

    del tasklist[0]
    assert not tasklist.tasks

    tasklist.tasks = [t1, t2, t3]
    count = 0
    for index, task in enumerate(tasklist):
        count += 1
        assert tasklist.tasks[index] == task
    assert count == 3

    popped = tasklist.pop(1)
    assert tasklist.tasks == [t1, t3]
    assert popped == t2
