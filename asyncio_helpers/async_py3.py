# THIS FILE WAS AUTO-GENERATED FROM `.\src\asyncio_helpers\async_py2.py`.
# !!! DO NOT EDIT !!!
from functools import wraps, partial

import asyncio

__all__ = ['sync']


def sync(async_wrapper):
    '''
    .. versionadded:: 0.2

    Return coroutine adapter for legacy asynchronous wrapper.

    Coroutine returns once wrapped function has finished executing.
    This decorator is useful for synchronizing execution of non-asyncio
    asynchronous functions.

    Notes
    -----

    Function **MUST** be wrapped within thread context where it will be yielded
    from.

    Parameters
    ----------
    async_wrapper : function
        Decorator that will execute the wrapped function in another thread.

    Example
    -------

    >>> from asyncio_helpers import sync
    >>> from pygtk_helpers.gthreads import gtk_threadsafe
    >>> # ...
    >>> @sync(gtk_threadsafe)
    >>> def ui_modifying_function():
    ...     # Modify UI state.
    ...     ...
    >>> async def coro():
    ...     # Call outside of GTK thread in a coroutine.
    ...     # Yield will return _after_ function has been executed in GTK
    ...     # thread.
    ...     result = await (ui_modifying_function())
    '''
    def _sync(f):
        '''
        Parameters
        ----------
        f : function or functools.partial
        '''
        loop = ensure_event_loop()
        done = asyncio.Event()

        @async_wrapper
        def _wrapped(*args):
            done.result = f(*args)
            loop.call_soon_threadsafe(done.set)
            return False

        _wrapped.loop = loop
        _wrapped.done = done

        wraps_func = f.func if isinstance(f, partial) else f

        @wraps(wraps_func)
        async def _synced(*args):
            _wrapped(*args)
            await (_wrapped.done.wait())
            return (_wrapped.done.result)

        return _synced
    return _sync
