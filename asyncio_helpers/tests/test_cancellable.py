# coding: utf-8
import asyncio

from concurrent.futures import ThreadPoolExecutor

from .. import cancellable
from nose.tools import raises, eq_


def test_cancellable_cancelled():

    async def _cancellable_test(duration_s):
        print('hello, world!')
        await asyncio.sleep(1.)
        print('goodbye, world!')

    _cancellable_test = cancellable(_cancellable_test)

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        future = loop.run_in_executor(executor, _cancellable_test, 1.)
        _cancellable_test.started.wait()
        _cancellable_test.cancel()
        with raises(asyncio.CancelledError):
            await future


def test_cancellable_done():
    async def _cancellable_test(duration_s_):
        return duration_s_

    _cancellable_test = cancellable(_cancellable_test)

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        duration_s = 1.
        future = loop.run_in_executor(executor, _cancellable_test, duration_s)
        result = loop.run_until_complete(future)
        eq_(duration_s, result)
