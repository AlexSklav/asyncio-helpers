# coding: utf-8
import asyncio
import functools
import platform
import threading

from typing import Coroutine, Union, Callable, Tuple, Any
from functools import wraps, partial

from logging_helpers import _L

from ._version import get_versions

__version__ = get_versions()['version']
del get_versions


def sync(async_wrapper: Coroutine) -> Callable:
    """
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
    """

    def _sync(f: Union[Callable, functools.partial]) -> Callable:
        """
        Parameters
        ----------
        f : function or functools.partial
        """
        loop = ensure_event_loop()
        done = asyncio.Event()

        async def _wrapped(*args) -> bool:
            done.result = await f(*args)
            loop.call_soon_threadsafe(done.set)
            return False

        _wrapped.loop = loop
        _wrapped.done = done

        wraps_func = f.func if isinstance(f, partial) else f

        @wraps(wraps_func)
        async def _synced(*args):
            await _wrapped(*args)
            await _wrapped.done.wait()
            return _wrapped.done.result

        return _synced

    return _sync


def cancellable(f):
    """
    Decorator to add `started` event attribute and `cancel()` method.

    The `cancel()` method cancels the running coroutine and by raising a
    `CancelledError` exception.

    Parameters
    ----------
    f : asyncio.coroutine

    Example
    -------

    >>> from asyncio_helpers import cancellable
    >>> import trollius as asyncio
    >>>
    >>> @cancellable
    ... @asyncio.coroutine
    ... def _cancellable_test(duration_s):
    ...     print('hello, world!')
    ...     yield asyncio.From(asyncio.sleep(1.))
    ...     print('goodbye, world!')
    >>>
    >>> with ThreadPoolExecutor() as executor:
    ...     future = executor.submit(_cancellable_test, 1.)
    ...     _cancellable_test.started.wait()
    ...     _cancellable_test.cancel()
    ...     future.result()  # raises `asyncio.CancelledError`


    .. versionchanged:: 0.2.1
        Retry cancelling tasks if a `RuntimeError` is raised.
    """
    started = threading.Event()

    @wraps(f)
    def _wrapped(*args, **kwargs):
        started.clear()
        started.loop = ensure_event_loop()
        started.set()
        return started.loop.run_until_complete(f(*args, **kwargs))

    def _cancel():
        loop = ensure_event_loop()
        current_task = asyncio.tasks.Task.current_task(loop=loop)
        while True:
            try:
                tasks_to_cancel = asyncio.Task.all_tasks(loop=loop)
                tasks = [task for task in tasks_to_cancel
                         if task is not current_task]
                break
            except RuntimeError as exception:
                # e.g., set changed size during iteration
                _L().debug(f'ERROR: {exception}', exc_info=True)
        list(map(lambda task: task.cancel(), tasks))

    _wrapped.started = started
    _wrapped.cancel = lambda: started.loop.call_soon_threadsafe(_cancel)
    return _wrapped


def new_file_event_loop():
    """
    Create an asyncio event loop compatible with file IO events, e.g., serial
    device events.

    On Windows, only sockets are supported by the default event loop (i.e.,
    :class:`asyncio.SelectorEventLoop`). However, file IO events _are_
    supported on Windows by the :class:`asyncio.ProactorEventLoop` event loop
    to support file I/O events.

    Returns
    -------
    asyncio.ProactorEventLoop or asyncio.SelectorEventLoop
    """
    return asyncio.new_event_loop()


def ensure_event_loop():
    """
    Ensure that an asyncio event loop has been bound to the local thread
    context.

    .. notes::
        While an asyncio event loop _is_ assigned to the local thread context
        for the main execution thread, other threads _do not_ have an event
        loop bound to the thread context.

    Returns
    -------
    asyncio.ProactorEventLoop or asyncio.SelectorEventLoop
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError as e:
        if 'There is no current event loop' in str(e):
            loop = new_file_event_loop()
            asyncio.set_event_loop(loop)
        else:
            raise
    return loop


def with_loop(func):
    """
    Decorator to run coroutine within an asyncio event loop.

    Parameters
    ----------
    func : asyncio.coroutine

    .. notes::
        Uses :class:`asyncio.ProactorEventLoop` on Windows to support file I/O
        events, e.g., serial device events.

        If an event loop is already bound to the thread, but is either a)
        currently running, or b) *not a :class:`asyncio.ProactorEventLoop`
        instance*, execute function in a new thread running a new
        :class:`asyncio.ProactorEventLoop` instance.

    Example
    -------

    >>> @with_loop
    ... @asyncio.coroutine
    ... def foo(a):
    ...     raise asyncio.Return(a)
    >>>
    >>> a = 'hello'
    >>> assert(foo(a) == a)
    """

    @wraps(func)
    def wrapped(*args, **kwargs):
        loop = ensure_event_loop()

        thread_required = False
        if loop.is_running():
            _L().debug('Event loop is already running.')
            thread_required = True
        elif all([platform.system() == 'Windows',
                  not isinstance(loop, asyncio.ProactorEventLoop)]):
            _L().debug(f'`ProactorEventLoop` required, not `{type(loop)}` loop in background thread.')
            thread_required = True

        if thread_required:
            _L().debug('Execute new loop in background thread.')
            finished = threading.Event()

            def _run(generator):
                loop = ensure_event_loop()
                try:
                    result = loop.run_until_complete(asyncio.ensure_future(generator))
                except Exception as e:
                    finished.result = None
                    finished.error = e
                else:
                    finished.result = result
                    finished.error = None
                finally:
                    loop.close()
                    _L().debug('closed event loop')
                finished.set()

            thread = threading.Thread(target=_run, args=(func(*args, **kwargs),))
            thread.daemon = True
            thread.start()
            finished.wait()
            if finished.error is not None:
                raise finished.error
            return finished.result

        _L().debug('Execute in exiting event loop in main thread')
        return loop.run_until_complete(func(**kwargs))

    return wrapped
