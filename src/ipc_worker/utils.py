# -*- coding: utf-8 -*-
# @Time    : 2021/11/30 10:22
# @Author  : tk

import logging
import time
from multiprocessing import Queue
from threading import Lock

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



# class RequestInfo:
#     def __int__(self,queue : Queue):
#         self.__last_t = time.time()
#         self.pending_request = {}
#         self.pending_response = {}
#         self.locker = Lock()
#         self.queue = queue
#
#     def add_request_id(self, request_id):
#         self.locker.acquire()
#         self.pending_request[request_id] = time.time()
#         self.locker.release()
#
#     def __clean__private__(self):
#         c_t = time.time()
#         if (c_t - self.__last_t) / 600 > 0:
#             self.__last_t = c_t
#             invalid = set({rid for rid, t in self.pending_request.items() if (c_t - t) / 3600 > 0})
#             logger.debug('remove {}'.format(str(list(invalid))))
#             for rid in invalid:
#                 self.pending_request.pop(rid)
#
#     def get(self, request_id):
#         response = None
#         while True:
#             is_end = False
#             self.locker.acquire(timeout=0.005)
#             if self.locker.locked():
#                 self.__clean__private__()
#             if request_id in self.pending_request:
#                 self.pending_request[request_id] = time.time()
#                 if request_id in self.pending_response:
#                     response = self.pending_response.pop(request_id)
#                     is_end = True
#                 else:
#                     r_id, w_id, seq_id, response = self.queue.get()
#                     if r_id != request_id:
#                         self.pending_response[r_id] = response
#                     else:
#                         is_end = True
#             else:
#                 logger.error('bad request_id {}'.format(request_id))
#                 is_end = True
#             if self.locker.locked():
#                 self.locker.release()
#             if is_end:
#                 break
#         return response