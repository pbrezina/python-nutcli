import re

import colorama

from nutcli.utils import Colorize


def test_Colorize_all__enabled():
    Colorize.enabled(True)

    result = Colorize.all('hello', colorama.Style.BRIGHT)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}hello{colorama.Style.RESET_ALL}'

    result = Colorize.all('hello', colorama.Style.BRIGHT, colorama.Fore.RED)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}{colorama.Fore.RED}hello{colorama.Style.RESET_ALL}'

    result = Colorize.all('', colorama.Style.BRIGHT)
    assert result == ''


def test_Colorize_all__disabled():
    Colorize.enabled(False)

    result = Colorize.all('hello', colorama.Style.BRIGHT)
    assert result == 'hello'

    result = Colorize.all('hello', colorama.Style.BRIGHT, colorama.Fore.RED)
    assert result == 'hello'


def test_Colorize_bold__enabled():
    Colorize.enabled(True)

    result = Colorize.bold('hello')
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}hello{colorama.Style.RESET_ALL}'


def test_Colorize_bold__disabled():
    Colorize.enabled(False)

    result = Colorize.bold('hello')
    assert result == 'hello'


def test_Colorize_re__enabled():
    Colorize.enabled(True)

    result = Colorize.re('hello', r'(.+)', colorama.Style.BRIGHT)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}hello{colorama.Style.RESET_ALL}'

    result = Colorize.re('hello', r'(.*)', colorama.Style.BRIGHT)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}hello{colorama.Style.RESET_ALL}'

    result = Colorize.re('hello', r'(he)(llo)', colorama.Style.BRIGHT, colorama.Fore.RED)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}he{colorama.Style.RESET_ALL}{colorama.Style.RESET_ALL}{colorama.Fore.RED}llo{colorama.Style.RESET_ALL}'

    result = Colorize.re('hello', r'(he(llo))', colorama.Style.BRIGHT, colorama.Fore.RED)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}he{colorama.Style.RESET_ALL}{colorama.Style.RESET_ALL}{colorama.Fore.RED}llo{colorama.Style.RESET_ALL}'

    result = Colorize.re('hello', r'(h(e)(llo))', colorama.Style.BRIGHT, colorama.Fore.RED, colorama.Fore.BLUE)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}h{colorama.Style.RESET_ALL}{colorama.Style.RESET_ALL}{colorama.Fore.RED}e{colorama.Style.RESET_ALL}{colorama.Style.RESET_ALL}{colorama.Fore.BLUE}llo{colorama.Style.RESET_ALL}'

    result = Colorize.re('hello', r'(h(e)(llo))', colorama.Style.BRIGHT, colorama.Fore.RED)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}h{colorama.Style.RESET_ALL}{colorama.Style.RESET_ALL}{colorama.Fore.RED}e{colorama.Style.RESET_ALL}llo'

    result = Colorize.re('hello', r'(h(e)llo)', colorama.Style.BRIGHT, colorama.Fore.RED)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}h{colorama.Style.RESET_ALL}{colorama.Style.RESET_ALL}{colorama.Fore.RED}e{colorama.Style.RESET_ALL}{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}llo{colorama.Style.RESET_ALL}'

    result = Colorize.re('hello', r'h(e)llo', colorama.Style.BRIGHT)
    assert result == f'h{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}e{colorama.Style.RESET_ALL}llo'

    result = Colorize.re('hello', r'(h(e)(llo))', colorama.Style.BRIGHT,
                         colorama.Fore.RED, [colorama.Fore.BLUE, colorama.Style.BRIGHT])
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}h{colorama.Style.RESET_ALL}{colorama.Style.RESET_ALL}{colorama.Fore.RED}e{colorama.Style.RESET_ALL}{colorama.Style.RESET_ALL}{colorama.Fore.BLUE}{colorama.Style.BRIGHT}llo{colorama.Style.RESET_ALL}'


def test_Colorize_re__enabled_compiled():
    Colorize.enabled(True)

    result = Colorize.re('hello', re.compile(r'(.+)'), colorama.Style.BRIGHT)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}hello{colorama.Style.RESET_ALL}'


def test_Colorize_re__disabled():
    Colorize.enabled(False)

    result = Colorize.re('hello', r'(.+)', colorama.Style.BRIGHT)
    assert result == 'hello'
