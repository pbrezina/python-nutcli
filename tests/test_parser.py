import argparse

from nutcli.parser import NegateAction, UniqueAppendAction, UniqueAppendConstAction


def test_UniqueAppendAction():
    parser = argparse.ArgumentParser()
    parser.add_argument('test', nargs='*', action=UniqueAppendAction)

    args = parser.parse_args([])
    assert args.test == []

    args = parser.parse_args(['1'])
    assert args.test == ['1']

    args = parser.parse_args(['1', '2'])
    assert args.test == ['1', '2']

    args = parser.parse_args(['1', '1'])
    assert args.test == ['1']

    args = parser.parse_args(['1', '2', '1', '2', '3'])
    assert args.test == ['1', '2', '3']


def test_UniqueAppendConstAction():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--1', nargs='*', action=UniqueAppendConstAction, dest='test', const='1'
    )
    parser.add_argument(
        '--2', nargs='*', action=UniqueAppendConstAction, dest='test', const='2'
    )
    parser.add_argument(
        '--3', nargs='*', action=UniqueAppendConstAction, dest='test', const='3'
    )

    args = parser.parse_args([])
    assert not args.test

    args = parser.parse_args(['--1'])
    assert args.test == ['1']

    args = parser.parse_args(['--1', '--2'])
    assert args.test == ['1', '2']

    args = parser.parse_args(['--1', '--1'])
    assert args.test == ['1']

    args = parser.parse_args(['--1', '--2', '--1', '--2', '--3'])
    assert args.test == ['1', '2', '3']


def test_NegateAction():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--arg', '--no-arg', action=NegateAction
    )

    args = parser.parse_args([])
    assert args.arg is None

    args = parser.parse_args(['--arg'])
    assert args.arg

    args = parser.parse_args(['--no-arg'])
    assert not args.arg
