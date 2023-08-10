# -*- coding: utf-8 -*-
# @Time    : 2021/11/29 15:06
# @Author  : tk
import multiprocessing
import os
from ipc_worker import logger
from ipc_worker.ipc_zmq_loader import IPC_zmq,ZMQ_process_worker

import torch
'''
    demo ZMQ depend zmq
    pip install pyzmq
    test pass >= python3.6
'''

tmp_dir = './tmp'
if not os.path.exists(tmp_dir):
    os.mkdir(tmp_dir)

os.environ['ZEROMQ_SOCK_TMP_DIR'] = tmp_dir

class My_worker(ZMQ_process_worker):
    def __init__(self,config,*args,**kwargs):
        super(My_worker,self).__init__(*args,**kwargs)
        #config info , use by yourself
        logger.info('Process id {}, group name {} , identity {}'.format(self._idx,self._group_name,self._identity))
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
        print(torch.cuda.device_count(),torch.cuda.current_device())


        if isinstance(request_data,dict):
            request_data['b'] = 200
        if self.handle is not None:
            #do some thing
            pass
        return request_data


if __name__ == '__main__':
    torch.multiprocessing.set_start_method('spawn',force=True)

    config = {
        "anything" : "anything",
        "aa": 100
    }

    evt_quit = multiprocessing.Manager().Event()

    # group_name 为共享内存组名,需唯一
    # manager is an agent  and act as a load balancing
    # worker is real doing your work
    instance = IPC_zmq(
        CLS_worker=My_worker,
        worker_args=(config,),  # must be tuple
        worker_num=10,  # number of worker Process
        group_name='serving_zmq',  # share memory name
        evt_quit=evt_quit,
        queue_size=20,  # recv queue size
        is_log_time=True,  # whether log compute time
        daemon=False,
    )
    instance.start()

    #demo produce and consume message , you can process by http
    for i in range(10):
        data = {"a" : 100}
        request_id = instance.put(data)

        data = instance.get(request_id)
        print('get process result',request_id,data)
    try:
        instance.join()
    except Exception as e:
        evt_quit.set()
        instance.terminate()
    del evt_quit