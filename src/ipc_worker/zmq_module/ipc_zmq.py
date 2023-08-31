# -*- coding: utf-8 -*-
# @Time    : 2021/11/29 13:45
# @Author  : tk
import math
import multiprocessing
import os
import random
import threading
import time
from typing import Optional

from .ipc_zmq_utils import ZMQ_manager,ZMQ_sink,ZMQ_worker
import pickle
from ..utils import logger
from collections import deque


class ZMQ_process_worker(ZMQ_worker):
    def __init__(self,*args,**kwargs):
        super(ZMQ_process_worker,self).__init__(*args,**kwargs)

    #Process begin trigger this func
    def run_begin(self):
        raise NotImplementedError

    # Process end trigger this func
    def run_end(self):
        raise NotImplementedError

    #any data put will trigger this func
    def run_once(self,request_data):
        raise NotImplementedError



class IPC_zmq:
    def __init__(self,
                 CLS_worker,
                 worker_args: tuple,
                 worker_num: int,
                 group_name,
                 evt_quit=multiprocessing.Manager().Event(),
                 queue_size=20,
                 is_log_time=False,
                 daemon=False
                 ):
        self.__manager_lst = []
        self.__woker_lst = []
        self.__group_idenity = []

        assert isinstance(worker_args, tuple)
        manager = ZMQ_manager(0, queue_size, group_name,evt_quit)
        self.__manager_lst.append(manager)

        sink = ZMQ_sink(queue_size,group_name,evt_quit)
        self.__manager_lst.append(sink)

        for i in range(worker_num):
            identity = bytes('{}_{}'.format(group_name,i),encoding='utf-8')
            worker = CLS_worker(
                *worker_args,
                identity=identity,
                group_name=group_name,
                evt_quit=evt_quit,
                is_log_time=is_log_time,
                idx=i,
                daemon=daemon
            )
            self.__group_idenity.append(identity)
            self.__woker_lst.append(worker)
        self.__last_worker_id = len(self.__group_idenity) - 1
        self.pending_request = {}
        self.pending_response = {}
        self.locker = threading.Lock()
        self.__last_t = time.time()
    def start(self):
        for w in self.__manager_lst:
            w.start()

        for w in self.__manager_lst:
            w.wait_init()


        for w in self.__woker_lst:
            w._set_addr(self.__manager_lst[1].addr,self.__manager_lst[0].addr)
            w.start()

        for w in self.__woker_lst:
            while not w.signal.is_set():
                pass
            del w.signal


    def put(self,data):
        self.__last_worker_id = (self.__last_worker_id + 1 ) % len(self.__group_idenity)
        idenity = self.__group_idenity[self.__last_worker_id]
        request_id = self.__manager_lst[0].put(idenity,pickle.dumps(data))
        self.locker.acquire()
        self.pending_request[request_id] = time.time()
        self.locker.release()
        return request_id

    # request_seq_id initail 1
    def get(self,request_id,request_seq_id=None):
        d = self._get_private(request_id,request_seq_id)
        return d if d is None else pickle.loads(d)

    def _check_and_clean(self):
        c_t = time.time()
        if math.floor((c_t - self.__last_t) / 600) > 0:
            self.__last_t = c_t
            invalid = set({rid for rid, t in self.pending_request.items() if math.floor((c_t - t) / 3600) > 0})
            logger.debug('remove {}'.format(str(list(invalid))))
            for rid in invalid:
                self.pending_request.pop(rid)
            invalid = set({rid for rid, t in self.pending_response.items() if math.floor((c_t - t["time"]) / 3600) > 0})
            for rid in invalid:
                self.pending_response.pop(rid)
    def _get_private(self, request_id,request_seq_id=None):
        sink = self.__manager_lst[1]
        response = None
        is_end = False
        timeout = 0.005
        while not is_end:
            self.locker.acquire(timeout=timeout)
            if not self.locker.locked():
                continue
            if request_id in self.pending_request:
                up_time = time.time()
                self.pending_request[request_id] = up_time
                reps = self.pending_response.get(request_id,None)
                if reps is not None:
                    reps["time"] = up_time
                    rep: Optional[deque] = reps["data"]
                    item_size = len(rep)
                    if item_size > 0:
                        if request_seq_id is None:
                            (seq_id,response) = rep.popleft()
                            is_end = True
                        else:
                            for i,rep_sub in enumerate(rep):
                                if rep_sub[0] == request_seq_id:
                                    (seq_id,response) = rep_sub
                                    rep.remove(rep_sub)
                                    is_end = True
                                    break

                    if len(rep) == 0:
                        self.pending_response.pop(request_id)

                if not is_end:
                    r_id, w_id, seq_id, response = sink.get_queue().get()
                    if r_id != request_id or (request_seq_id is not None and request_seq_id != seq_id):
                        if r_id in self.pending_response:
                            rep: Optional[deque] = self.pending_response[r_id]["data"]
                            for i,node in enumerate(rep):
                                if seq_id > node[0]:
                                    rep.insert(i+1,(seq_id,response))
                                    break
                        else:
                            self.pending_response[r_id] = {
                                "time": time.time(),
                                "data": deque([(seq_id,response)]),
                                "last_seq": seq_id - 1,
                            }
                    else:
                        is_end = True
            else:
                logger.error('bad request_id {}'.format(request_id))
                is_end = True
            self._check_and_clean()
            if self.locker.locked():
                self.locker.release()
            if is_end:
                break
        return response

    def join(self):
        for p in self.__manager_lst:
            p.join()
        time.sleep(1)
        for p in self.__woker_lst:
            p.join()

    @property
    def manager_process_list(self):
        return self.__manager_lst

    @property
    def woker_process_list(self):
        return self.__woker_lst

    def terminate(self):
        for p in self.__woker_lst + self.__manager_lst:
            try:
                p.release()
            except Exception as e:
                pass
            p.terminate()