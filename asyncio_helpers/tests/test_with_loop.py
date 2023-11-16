# coding: utf-8
import asyncio

from .. import with_loop
from nose.tools import eq_


def test_with_loop():
    async def foo(a_):
        return a_

    foo = with_loop(foo)

    a = 'hello'

    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(foo(a))
    eq_(result, a)

