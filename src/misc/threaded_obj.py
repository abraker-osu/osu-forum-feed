import threading
from typing import TypeVar, Generic, Iterator


T = TypeVar('T')


class Threaded(Generic[T]):

    def __init__(self, obj: T = None):
        self.__lock = threading.Lock()
        self.__obj  = obj


    def __getattr__(self, name: str):
        """Intercept attribute access to wrap method calls with the lock."""
        attr = getattr(self.__obj, name)
        if callable(attr):
            def locked_method(*args, **kwargs):
                with self.__lock:
                    return attr(*args, **kwargs)
            return locked_method

        return attr


    def __iter__(self) -> Iterator:
        assert isinstance(self.__obj, Iterator)

        with self.__lock:
            return ( obj.get() if isinstance(obj, Threaded) else obj for obj in self.__obj )


    def __repr__(self) -> str:
        with self.__lock: return f'{self.__obj}'


    def get(self) -> T:
        return self.__obj


    def set(self, obj: T):
        if isinstance(obj, Threaded):
            obj = obj.get()

        with self.__lock:
            self.__obj = obj


    def __iadd__(self, other: T) -> 'Threaded':
        with self.__lock:
            self.__obj += other
            return self


    def __isub__(self, other: T) -> 'Threaded':
        with self.__lock:
            self.__obj -= other
            return self


    def __imul__(self, other: T) -> 'Threaded':
        with self.__lock:
            self.__obj *= other
            return self


    def __itruediv__(self, other: T) -> 'Threaded':
        with self.__lock:
            self.__obj /= other
            return self


    def __add__(self, other: T) -> T:
        return self.__obj + other

    def __radd__(self, other: T) -> T:
        return self.__add__(other)

    def __sub__(self, other: T) -> T:
        return self.__obj - other

    def __rsub__(self, other: T) -> T:
        return other - self.__obj

    def __mul__(self, other: T) -> T:
        return self.__obj * other

    def __rmul__(self, other: T) -> T:
        return self.__mul__(other)

    def __truediv__(self, other: T) -> T:
        return self.__obj / other

    def __rtruediv__(self, other: T) -> T:
        return other / self.__obj

    def __floordiv__(self, other: T) -> T:
        return self.__obj // other

    def __rfloordiv__(self, other: T) -> T:
        return other // self.__obj

    def __mod__(self, other: T) -> T:
        return self.__obj % other

    def __rmod__(self, other: T) -> T:
        return other % self.__obj

    def __pow__(self, other: T) -> T:
        return self.__obj ** other

    def __rpow__(self, other: T) -> T:
        return other ** self.__obj

    def __eq__(self, other: T) -> bool:
        return self.__obj == other

    def __ne__(self, other: T) -> bool:
        return self.__obj != other

    def __lt__(self, other: T) -> bool:
        return self.__obj < other

    def __gt__(self, other: T) -> bool:
        return self.__obj > other

    def __le__(self, other: T) -> bool:
        return self.__obj <= other

    def __ge__(self, other: T) -> bool:
        return self.__obj >= other
