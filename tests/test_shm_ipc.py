# -*- coding: utf-8 -*-
# @Time    : 2021/11/23 9:35

'''
demo share memrory
recommended system linux and python >= 3.8
    recommended linux
    python 3.8

Do not recommended run in windows , it will report an error as follow
    RuntimeError:
            An attempt has been made to start a new process before the
            current process has finished its bootstrapping phase.

'''

import multiprocessing
import os
from ipc_worker import logger
from ipc_worker.ipc_shm_loader import IPC_shm,SHM_process_worker


class My_worker(SHM_process_worker):
    def __init__(self,config,*args,**kwargs):
        super(My_worker,self).__init__(*args,**kwargs)
        #config info , use by yourself

        logger.info('Process id {}, group name {} ,shm name {}'.format(self._idx,self._group_name,self._shm_name))
        logger.info(config)
        self.config = config


    #Process begin trigger this func
    def run_begin(self):
        logger.info('worker pid {}...'.format(os.getpid()))
        self.handle = None
        pass

    # Process end trigger this func
    def run_end(self):
        if self.handle is not None:
            pass

    #any data put will trigger this func
    def run_once(self,request_data):
        #process request_data
        if isinstance(request_data,dict):
            request_data['b']  = 200
        if self.handle is not None:
            #do some thing
            pass
        return request_data


if __name__ == '__main__':
    config = {
        "anything" : "anything",
        "aa": 100
    }

    evt_quit = multiprocessing.Manager().Event()

    # group_name 为共享内存组名,需唯一
    # manager is an agent  and act as a load balancing
    # worker is real doing your work
    instance = IPC_shm(
        CLS_worker=My_worker,
        worker_args=(config,),  # must be tuple
        worker_num=10,  # number of worker Process
        manager_num=2,  # number of agent Process
        group_name='serving_shm',  # share memory name
        shm_size=1 * 1024 * 1024,  # share memory size
        queue_size=20,  # recv queue size
        is_log_time=True,  # whether log compute time
        daemon=False,
    )

    instance.start()

    #demo produce and consume message , you can process by http
    for i in range(10):
        print('produce message')
        data = {"a" : 100}
        request_id = instance.put(data)
        data = instance.get(request_id)
        print('get process result',data)
    try:
        instance.join()
    except Exception as e:
        evt_quit.set()
        instance.terminate()

    del evt_quit