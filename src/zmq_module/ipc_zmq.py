# -*- coding: utf-8 -*-
# @Time    : 2021/11/29 13:45
# @Author  : tk
import multiprocessing
import random
import time

from .ipc_zmq_utils import ZMQ_manager,ZMQ_sink,ZMQ_worker
import pickle



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

        #ZMQ_worker(identity,evt_quit,ip,port, port_out)

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
            #worker.start()

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
        idenity = random.choice(self.__group_idenity)
        request_id = self.__manager_lst[0].put(idenity,pickle.dumps(data))
        self.__manager_lst[1].add_request_id(request_id)
        return request_id

    def get(self,request_id):
        #data has serializated
        d = self.__manager_lst[1].get(request_id)
        return d if d is None else pickle.loads(d)

    def join(self):
        for p in self.__manager_lst:
            p.join()
        time.sleep(1)
        for p in self.__woker_lst:
            p.join()

    def terminate(self):
        for p in self.__woker_lst:
            try:
                p.close()
            except Exception as e:
                pass
            p.terminate()
        for p in self.__manager_lst:
            try:
                p.close()
            except Exception as e:
                pass
            p.terminate()