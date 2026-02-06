import asyncio
import contextvars
import threading
from core.classes.modules.dthreads.dthread import DaemonThreadPoolExecutor
import core.definition as dfn
from typing import TYPE_CHECKING, Any, Callable, Optional, Union, Coroutine

if TYPE_CHECKING:
    from core.loader import Loader


class DAsyncio:

    def __init__(self, loader: 'Loader'):
        self.ctx = loader
        self.logs = loader.Logs

        self.running_iotasks: list[dfn.DTask] = self.ctx.Settings.RUNNING_ASYNC_TASKS
        self.running_iothreads: list[dfn.MThread] = self.ctx.Settings.RUNNING_ASYNC_THREADS

    def create_task(self,
                    func: Callable[..., Coroutine[Any, Any, Any]],
                    *args,
                    task_name: Optional[str] = None,
                    run_once: bool = False,
                    task_flag: bool = False) -> Optional[dfn.DTask]:
        task_event: Optional[asyncio.Event] = None
        largs = list(args)
        if task_flag:
            task_event = asyncio.Event()
            task_event.set()
            largs.insert(0, task_event)
        
        _task = self.__create_asynctask(func(*tuple(largs)),
                                        async_name=task_name,
                                        run_once=run_once)

        _dtask = dfn.DTask(_task, task_event)
        self.running_iotasks.append(_dtask)

        return _dtask

    def create_safe_task(self, func: Coroutine[Any, Any, Any], *,
                         async_name: str = None,
                         run_once: bool = False
                         ) -> Optional[dfn.DTask]:
        """Create a new asynchrone and store it into running_iotasks variable
        WARNING: Use this is you are sure that the func will be stopped.
        Args:
            func (Callable): The function you want to call in asynchrone way
            async_name (str, optional): The task name. Defaults to None.
            run_once (bool, optional): If true the task will be run once. Defaults to False.

        Returns:
            dfn.DTask: The DTask Object
        """
        name = func.__name__ if async_name is None else async_name
        self.ctx.Settings.TASKS_CTX.set(name)
        io_ctx = contextvars.copy_context()

        if run_once:
            for task in asyncio.all_tasks():
                if task.get_name().lower() == name.lower():
                    return None

        _task = asyncio.create_task(func, name=name)
        _task.add_done_callback(self.__asynctask_done, context=io_ctx)

        _dtask = dfn.DTask(_task, None)
        self.running_iotasks.append(_dtask)

        self.logs.debug(f"[IO SAFE TASK CREATE] Name: {_task.get_name()}")
        return _dtask

    async def create_io_thread(self, func: Callable[..., object], *args,
                               thread_name: str = '', run_once: bool = False,
                               thread_flag: bool = False
                               ) -> Optional[Any]:
        """Run threads via asyncio.

        Args:
            func (Callable[..., Any]): The blocking IO function
            run_once (bool, optional): If it should be run once.. Defaults to False.
            thread_flag (bool, optional): If you are using a endless loop, use the threading Event object. Defaults to False.

        Returns:
            Any: The final result of the blocking IO function
        """
        _name = thread_name if thread_name else func.__name__
        self.ctx.Settings.TASKS_CTX.set(_name)
        io_ctx = contextvars.copy_context()

        if run_once:
            for iothread in self.running_iothreads:
                _thread = iothread.thread_obj
                if _name.lower() == iothread.name.lower():
                    self.logs.debug(f"[IO THREAD RUNNING] ID: {_thread.native_id} | NAME: {_thread.name}")
                    return None

        executor = DaemonThreadPoolExecutor(daemon=True)
        executor.start(max_workers=1, thread_name_prefix=_name)
        loop = asyncio.get_event_loop()
        largs = list(args)
        thread_event: Optional[threading.Event] = None
        if thread_flag:
            thread_event = threading.Event()
            thread_event.set()
            largs.insert(0, thread_event)

        future = loop.run_in_executor(executor, func, *tuple(largs))
        future.add_done_callback(self.__asynctask_done, context=io_ctx)
        _thread = list(executor._threads)[0]
        _thread.name = _name

        id_obj = self.ctx.Definition.MThread(
            name=_name,
            thread_id=_thread.native_id,
            thread_event=thread_event,
            thread_obj=_thread,
            executor=executor,
            future=future)

        self.running_iothreads.append(id_obj)
        self.logs.debug(f"[IO THREAD START] ID: {_thread.native_id} | NAME: {_thread.name} | WORKERS: {executor._max_workers}")
        result = await future

        self.running_iothreads.remove(id_obj)
        return result

    def __create_asynctask(self, func: Coroutine[Any, Any, Any], *, async_name: str = None, run_once: bool = False) -> Optional[asyncio.Task]:
        """Create a new asynchrone and store it into running_iotasks variable

        Args:
            func (Callable): The function you want to call in asynchrone way
            async_name (str, optional): The task name. Defaults to None.
            run_once (bool, optional): If true the task will be run once. Defaults to False.

        Returns:
            asyncio.Task: The Task
        """
        name = func.__name__ if async_name is None else async_name
        self.ctx.Settings.TASKS_CTX.set(name)
        io_ctx = contextvars.copy_context()

        if run_once:
            for task in asyncio.all_tasks():
                if task.get_name().lower() == name.lower():
                    return None

        task = asyncio.create_task(func, name=name)
        task.add_done_callback(self.__asynctask_done, context=io_ctx)
        self.logs.debug(f"[IO TASK CREATE] Name: {task.get_name()}")
        return task

    def __asynctask_done(self,
                         task: Union[asyncio.Task, asyncio.Future],
                         context: Optional[dict[str, Any]] = None
                         ) -> None:
        """Log task when done

        Args:
            task (asyncio.Task): The Asyncio Task callback
        """
        _context = context
        task_name = self.ctx.Settings.TASKS_CTX.get()
        task_or_future = "Task"
        try:
            if task.exception():
                self.logs.error(f"[IO TASK CRASHED] {task_or_future} {task_name} failed with exception: {task.exception()}")
            else:
                self.logs.debug(f"[IO TASK COMPLETED] {task_or_future} {task_name} completed successfully.")
        except asyncio.CancelledError as ce:
            self.logs.debug(f"[IO TASK CRASHED] {task_or_future} {task_name} terminated with cancelled error. {ce}")
        except asyncio.InvalidStateError as ie:
            self.logs.debug(f"[IO TASK CRASHED] {task_or_future} {task_name} terminated with invalid state error. {ie}")
