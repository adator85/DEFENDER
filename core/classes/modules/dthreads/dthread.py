import asyncio
import threading
from time import sleep
from dataclasses import dataclass
from typing import Callable, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.loader import Loader

@dataclass
class ThreadModel:
    func: Callable[[Any], Any]
    name: str
    args: tuple
    kwargs: dict
    daemon: bool
    loop: bool
    t_event: Optional[threading.Event]
    thread: Optional[threading.Thread]

def deco_thread(func):
    # Step 2: Define the wrapper function
    def wrapper(*args, **kwargs):
        _current_thread = threading.current_thread()
        print(f"Register new Thread {_current_thread.name}")
        result = func(*args, **kwargs)  # Call the original function
        print(f"Thread {_current_thread.name} has been stopped")
        return result

    return wrapper

class DThread:

    def __init__(self, ctx: 'Loader'):
        self._threads: list[ThreadModel] = []
        self._logs = ctx.Logs

    @property
    def threads(self) -> list[ThreadModel]:
        return self._threads

    def add_task(self, func, *args, name: str = None,
                 daemon: bool = False, loop: bool = False,
                 run_once: bool = True,
                 **kwargs) -> Optional[ThreadModel]:
        """This register the task and prepare it to be used in a thread

        Args:
            func (_type_): The function you want to execute in a thread
            name (str, optional): The name of the thread. Defaults to None.
            daemon (bool, optional): Is it daemon. Defaults to False.
            loop (bool, optional): If you want to pass and event to stop the loop
                if true, you will have to pass as a first arg into your function
                an event variable (threading.Event). Defaults to False.
            run_once (bool, optional): Make sure this thread is running once. Defaults to True.

        Returns:
            Optional[ThreadModel]: The thread model or None
        """

        _func = func
        _name = func.__name__ if name is None else name
        _daemon = daemon
        _loop = loop
        _run_once = run_once
        _kwargs = kwargs
        _event = None

        if _run_once:
            th = self.get_thread(_name)
            if th is not None:
                print("Thread already running!")
                return None

        if loop:
            _args = list(args)
            _event = threading.Event()
            _event.set()
            _args.insert(0, _event)
            _args = tuple(_args)
        else:
            _args = args

        _model = ThreadModel(
            _func, _name, _args, _kwargs, _daemon, _loop,
            t_event=_event, thread=None
        )
        self._threads.append(_model)
        return _model

    def get_thread(self, name: str) -> Optional[ThreadModel]:
        for thread in self._threads:
            if thread.name.lower() == name.lower():
                return thread

        return None

    @staticmethod
    def start(*args: ThreadModel) -> None:

        for task in args:
            if isinstance(task, ThreadModel):
                thd = threading.Thread(
                    target=task.func,
                    name=task.name,
                    args=task.args,
                    daemon=task.daemon
                )

                thd.start()
                task.thread = thd
                print("Starting Thread", thd.name, "N°", thd.native_id)
            else:
                print(f"Cannot run {task}")

    def stop(self, *args: ThreadModel) -> None:
        for task in args:
            if isinstance(task, ThreadModel):
                if self.get_thread(task.name) is not None:
                    print(f"Clearing thread N°{task.thread.native_id}: {task.name}")
                    task.t_event.clear() if isinstance(task.t_event, threading.Event) else None
                    try:
                        task.thread.join()
                    except RuntimeError as re:
                        print(f"Issue on thread N°{task.thread.native_id}: {task.thread.name}", re)
                    self._threads.remove(task)
                    print(f"Thread {task.name} has been removed!")

    @staticmethod
    def join(*args: ThreadModel):
        for task in args:
            if isinstance(task, ThreadModel):
                task.thread.join(5)

# def run_blocking_loop(t_event: threading.Event, my_param_in_args):
#     while t_event.is_set():
#         sleep(2)
#         print("My arg:", my_param_in_args)

# @deco_thread
# def run_blocking_func(wait):
#     sleep(wait)

# def threads_clean(thread_obj: DThread):
#     if isinstance(thread_obj, DThread):
#         _threads = thread_obj.threads.copy()
#         for thd in _threads:
#             thread_obj.stop(thd)
#         del _threads


# async def main():
#     thread = DThread()
#     count = 0

#     thread_1 = thread.add_task(
#         run_blocking_loop, "My param 1", name='thread_task_1', loop=True
#     )
#     thread_4 = thread.add_task(
#         run_blocking_loop, "My param 4", name='thread_task_4', loop=True
#     )
#     thread_2 = thread.add_task(
#         run_blocking_loop, "My param 2", name='thread_task_2', loop=True
#     )
#     thread_3 = thread.add_task(
#         run_blocking_func, 5, name='thread_task_3'
#     )

#     # clean = thread.add_task(
#     #     threads_clean, thread, name='threads_clean'
#     # )

#     while True:
#         await asyncio.sleep(0.5)

#         if count == 2:
#             # Start thread 1
#             thread.start(thread_1, thread_3, thread_4)

#         if count == 3:
#             thread.start(thread_2)

#         if count == 10:
#             # thread.start(clean)
#             threads_clean(thread)
#             break

#         count += 1

#     print("End of asyncio")


# if __name__ == '__main__':
#     asyncio.run(main())
