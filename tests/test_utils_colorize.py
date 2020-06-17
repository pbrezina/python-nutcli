import re

import colorama
import mock

from nutcli.utils import Colorize


@mock.patch(
    'nutcli.utils.Colorize.print_colors',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_Colorize_all__enabled(_):
    result = Colorize.all('hello', colorama.Style.BRIGHT)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}hello{colorama.Style.RESET_ALL}'

    result = Colorize.all('hello', colorama.Style.BRIGHT, colorama.Fore.RED)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}{colorama.Fore.RED}hello{colorama.Style.RESET_ALL}'

    result = Colorize.all('', colorama.Style.BRIGHT)
    assert result == ''


@mock.patch(
    'nutcli.utils.Colorize.print_colors',
    new_callable=mock.PropertyMock,
    return_value=False
)
def test_Colorize_all__disabled(_):
    result = Colorize.all('hello', colorama.Style.BRIGHT)
    assert result == 'hello'

    result = Colorize.all('hello', colorama.Style.BRIGHT, colorama.Fore.RED)
    assert result == 'hello'


@mock.patch(
    'nutcli.utils.Colorize.print_colors',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_Colorize_bold__enabled(_):
    result = Colorize.bold('hello')
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}hello{colorama.Style.RESET_ALL}'


@mock.patch(
    'nutcli.utils.Colorize.print_colors',
    new_callable=mock.PropertyMock,
    return_value=False
)
def test_Colorize_bold__disabled(_):
    result = Colorize.bold('hello')
    assert result == 'hello'


@mock.patch(
    'nutcli.utils.Colorize.print_colors',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_Colorize_re__enabled(_):
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


@mock.patch(
    'nutcli.utils.Colorize.print_colors',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_Colorize_re__enabled_compiled(_):
    result = Colorize.re('hello', re.compile(r'(.+)'), colorama.Style.BRIGHT)
    assert result == f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}hello{colorama.Style.RESET_ALL}'


@mock.patch(
    'nutcli.utils.Colorize.print_colors',
    new_callable=mock.PropertyMock,
    return_value=False
)
def test_Colorize_re__disabled(_):
    result = Colorize.re('hello', r'(.+)', colorama.Style.BRIGHT)
    assert result == 'hello'
