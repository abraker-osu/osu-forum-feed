import threading
import time



class ThreadEnchanced(threading.Thread):

    __THREAD_TIMEOUT = 10

    def __init__(self, *args, **kwargs):
        assert 'target' in kwargs
        assert 'args'   in kwargs
        assert type(kwargs['args'][0]) == threading.Event
        assert type(kwargs['args'][1]) == threading.Event

        self.__start_time = None

        # Notified by the target to the thread
        self.__target_event: threading.Event = kwargs['args'][0]

        # Notified by the thread to the target
        self.__thread_event: threading.Event = kwargs['args'][1]

        threading.Thread.__init__(self, *args, **kwargs)


    def run(self):
        self.__start_time = time.time()
        threading.Thread.run(self)
        self.__target_event.wait(self.__THREAD_TIMEOUT)


    def stop(self):
        self.__target_event.clear()
        self.__thread_event.set()
        self.__target_event.wait(self.__THREAD_TIMEOUT)


    @property
    def runtime(self):
        if self.__start_time is not None:
            return time.time() - self.__start_time

        return 0
