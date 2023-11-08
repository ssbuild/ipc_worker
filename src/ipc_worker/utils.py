# -*- coding: utf-8 -*-
# @Time    : 2021/11/30 10:22
# @Author  : tk

import logging
import threading

from termcolor import colored


def set_logger(context, verbose=False):
    # if os.name == 'nt':  # for Windows
    #     return NTLogger(context, verbose)

    logger = logging.getLogger(context)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    formatter = logging.Formatter(
        '%(levelname)-.1s:' + context + ':[%(filename)s:%(funcName)s:%(lineno)3d]:%(message)s', datefmt=
        '%m-%d %H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(console_handler)
    return logger


logger = set_logger(colored('VENTILATOR', 'magenta'))



class RLock:
    def __init__(self):
        self._lock = threading.RLock()

    def __enter__(self):
        return self._lock.__enter__()
    def __exit__(self, t, v, tb):
        return self._lock.__exit__(t,v,tb)
    def __repr__(self):
        return self._lock.__repr__()


    def acquire(self):
        self._lock.acquire()

    def release(self):
        self._lock.release()

    def __getstate__(self):
        return {}

    def __setstate__(self, state):
        self.__init__()


class Lock:
    def __init__(self):
        self._lock = threading.Lock()

    def __enter__(self):
        return self._lock.__enter__()

    def __exit__(self, t, v, tb):
        return self._lock.__exit__(t, v, tb)

    def __repr__(self):
        return self._lock.__repr__()

    def acquire(self):
        self._lock.acquire()

    def release(self):
        self._lock.release()

    def __getstate__(self):
        return {}

    def __setstate__(self, state):
        self.__init__()