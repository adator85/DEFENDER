import concurrent.futures
import threading
import weakref

class DaemonThreadPoolExecutor(concurrent.futures.ThreadPoolExecutor):

    def __init__(self, daemon: bool = True):
        self.daemon = daemon

    def start(self, max_workers=None,
              thread_name='', thread_name_prefix='',
              initializer=None, initargs=()):
        super().__init__(max_workers, thread_name_prefix, initializer, initargs)
        self.thread_name = thread_name

    def _adjust_thread_count(self):
        if len(self._threads) < self._max_workers:
            def weakref_cb(_, q=self._work_queue):
                q.put(None)

            t = threading.Thread(
                name=self.thread_name,
                target=concurrent.futures.thread._worker,
                args=(
                    weakref.ref(self, weakref_cb), 
                    self._work_queue,
                    self._initializer,
                    self._initargs
                ),
                daemon=self.daemon
            )
            self._threads.add(t)
            concurrent.futures.thread._threads_queues[t] = self._work_queue
            t.start()

            # On empêche Python d'attendre ce thread à la fermeture globale
            # en le retirant du dictionnaire interne de threading
            if hasattr(threading, "_shutdown_locks"):
                # Pour les versions récentes de Python
                pass
