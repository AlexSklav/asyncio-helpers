from __future__ import absolute_import, unicode_literals, print_function
import logging
import re


def trollius_to_async(input_filename):
    'Convert Python 2 async code using trollius to Python 3 async syntax.'
    assert(input_filename.endswith('_py2.py'))
    output_filename = input_filename.rstrip('_py2.py') + '_py3.py'

    with open(input_filename, 'r') as input_:
        data = input_.read()

    print('Read Python 2 content from: `%s`' % input_filename)

    cre_yield_from = re.compile(r'yield asyncio.From\((.*?)\)$',
                                flags=re.MULTILINE | re.DOTALL)
    cre_coro = re.compile(r'@asyncio\.coroutine\W*def',
                          flags=re.MULTILINE | re.DOTALL)
    cre_return = re.compile(r'raise\W+asyncio\.Return\((.*?)\)$',
                            flags=re.MULTILINE | re.DOTALL)

    with open(output_filename, 'w') as output:
        output_data = ('# THIS FILE WAS AUTO-GENERATED FROM '
                       '`%s`.\n# !!! DO NOT EDIT !!!\n%s' %
                       (input_filename, data))
        output_data = output_data.replace('import trollius as asyncio',
                                          'import asyncio')
        output_data = cre_coro.sub(r'async def', output_data)
        output_data = cre_yield_from.sub(r'await (\1)', output_data)
        output_data = cre_return.sub(r'return (\1)', output_data)
        output.write(output_data)
    print('Wrote Python 3 content to: `%s`' % output_filename)


def main():
    import sys

    trollius_to_async(sys.argv[1])


if __name__ == '__main__':
    main()
