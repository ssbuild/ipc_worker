#coding: utf-8
import multiprocessing
import time
from threading import Lock
from .ipc_shm_utils import SHM_manager,SHM_woker
import pickle
# import numpy as np
class SHM_process_worker(SHM_woker):
    def __init__(self,*args,**kwargs):
        super(SHM_process_worker,self).__init__(*args,**kwargs)

    #Process begin trigger this func
    def run_begin(self):
        raise NotImplementedError

    # Process end trigger this func
    def run_end(self):
        raise NotImplementedError

    #any data put will trigger this func
    def run_once(self,request_data):
        raise NotImplementedError



class IPC_shm:
    def __init__(self,
                 CLS_worker,
                 worker_args: tuple,
                 worker_num: int,
                 manager_num: int,
                 group_name,
                 evt_quit=multiprocessing.Manager().Event(),
                 shm_size=1 * 1024 * 1024,
                 queue_size=20,
                 is_log_time=False,
                 daemon=False
                 ):
        self.__manager_lst = []
        self.__woker_lst = []
        self.__signal_list = []
        self.__shm_name_list = []

        self.__input_queue = None
        self.__output_queue = None


        self.request_id = 0
        self.pending_request = {}
        self.pending_response = {}

        self.locker = Lock()

        assert isinstance(worker_args, tuple)
        self.__input_queue = multiprocessing.Manager().Queue(queue_size)
        self.__output_queue = multiprocessing.Manager().Queue(queue_size)

        semaphore = multiprocessing.Manager().Semaphore(worker_num)

        for i in range(worker_num):
            shm_name = '{}_jid_{}'.format(group_name, i)
            worker = CLS_worker(
                *worker_args,
                evt_quit,
                semaphore,
                shm_name,
                shm_size,
                is_log_time=is_log_time,
                idx=i,
                group_name=group_name,
                daemon=daemon)
            self.__signal_list.append(worker.get_signal())
            self.__shm_name_list.append(shm_name)
            self.__woker_lst.append(worker)

        semaphore = multiprocessing.Manager().Semaphore(manager_num)
        for i in range(manager_num):
            manager = SHM_manager(evt_quit,
                                  self.__signal_list,
                                  semaphore,
                                  self.__shm_name_list,
                                  self.__input_queue,
                                  self.__output_queue,
                                  is_log_time=is_log_time,
                                  idx=i)
            self.__manager_lst.append(manager)
        self.__last_t = time.time()
    def start(self):
        for w in self.__woker_lst:
            w.start()
        for w in self.__manager_lst:
            w.start()

    def put(self,data):
        self.locker.acquire()
        self.request_id += 1
        request_id = self.request_id
        self.pending_request[request_id] = time.time()
        self.__input_queue.put((request_id,pickle.dumps(data)))
        self.locker.release()
        return request_id

    def __clean__private__(self):
        c_t = time.time()
        if (c_t - self.__last_t) / 600 > 0:
            self.__last_t = c_t
            invalid = set({rid for rid, t in self.pending_request.items() if (c_t - t) / 3600 > 0})
            for rid in invalid:
                self.pending_request.pop(rid)

    def get(self,request_id):
        response = None
        while True:
            is_end = False
            self.locker.acquire(blocking=False)
            if self.locker.locked():
                self.__clean__private__()

            if request_id in self.pending_request:
                self.pending_request[request_id] = time.time()
                if request_id in self.pending_response:
                    response = self.pending_response.pop(request_id)
                    is_end = True
                else:
                    r_id,_,seq_id, response = self.__output_queue.get()
                    if r_id != request_id:
                        self.pending_response[r_id] = response
                    else:
                        is_end = True
            else:
                print('bad request_id {}'.format(request_id))
                is_end = True
            if self.locker.locked():
                self.locker.release()
            if is_end:
                break
        return response

    def join(self):
        for p in self.__manager_lst:
            p.join()
        for p in self.__woker_lst:
            p.join()

    def terminate(self):
        for p in self.__woker_lst + self.__manager_lst:
            try:
                p.release()
            except Exception as e:
                pass
            p.terminate()

    @property
    def manager_process_list(self):
        return self.__manager_lst

    @property
    def woker_process_list(self):
        return self.__woker_lst