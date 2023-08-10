# -*- coding: utf-8 -*-
# @Time    : 2021/11/23 9:33
# @Author  : tk
import json
import random
import struct
import multiprocessing
import traceback
from multiprocessing import Event,Condition,Process
from datetime import datetime
import numpy as np
import pickle
import typing
from .ipc_utils_func import C_sharedata, WorkState
from ..utils import logger


class SHM_manager(Process):
    def __init__(self,evt_quit,
                 signal_list,semaphore,
                 shm_name_list,
                 input_queue,
                 output_queue,
                 is_log_time,
                 idx,
                 daemon=False):
        super().__init__(daemon=daemon)
        self._evt_quit = evt_quit
        self._signal_list = signal_list

        self._semaphore = semaphore
        self._shm_name_list = shm_name_list

        self._input_queue = input_queue
        self._output_queue = output_queue

        self._is_log_time = is_log_time
        self.idx = idx
        # self.input_queue = multiprocessing.Manager().Queue(queue_size),
        # self.output_queue = multiprocessing.Manager().Queue(1)

    def get_input_queue(self):
        return self._input_queue

    def get_output_queue(self):
        return self._output_queue

    def get_real_data(self,buf):
        len = struct.unpack('i',buf[12:16])[0]
        d = buf[16:16+len]
        #队列不能序列化 bytes
        return pickle.loads(d)

    def release(self):
        if not getattr(self,'__is_closed',False):
            self._input_queue.close()
            self._output_queue.close()
            setattr(self,'__is_closed',True)

    def run(self):
        shm_list = []
        for shm_name in self._shm_name_list:
            s_d = C_sharedata(name=shm_name,create=False)
            shm_list.append(s_d)
        task_queue1 = self._input_queue
        task_queue2 = self._output_queue

        s_d_id_list = []
        try:
            while True:
                request_id,msg = task_queue1.get()
                if self._evt_quit.is_set():
                    break
                s_d_id_list.clear()
                self._semaphore.acquire()
                for i,node in enumerate(shm_list):
                    flag = struct.unpack("i", node.buf[0:4])[0]
                    if flag == WorkState.WS_FREE:
                        s_d_id_list.append(i)
                if len(s_d_id_list) == 0:
                    self._semaphore.release()
                    logger.info('service busy  , no worker consume')
                    task_queue1.put((request_id,msg))
                    continue
                sel_id = random.choices(s_d_id_list)[0]
                s_d = shm_list[sel_id]

                #if isinstance(msg,dict) else msg
                # d = pickle.dumps(msg)
                # print(d)

                d = msg
                s_d.buf[12:16] = struct.pack("i", len(d))
                s_d.buf[16:16 + len(d)] = d
                s_d.buf[0:4] = struct.pack("i", WorkState.WS_REQUEST)
                #是否信号，给其他进程
                self._semaphore.release()
                self._signal_list[sel_id].set()
                start_t = datetime.now()
                Flag_step = False
                while True:
                    flag = struct.unpack("i", s_d.buf[0:4])[0]
                    if flag == WorkState.WS_FINISH:
                        break
                    elif flag == WorkState.WS_FINISH_STEP:
                        Flag_step = True
                        p_result = self.get_real_data(s_d.buf)
                        worker_id = struct.unpack("i", s_d.buf[4:8])[0]
                        seq_id = struct.unpack("i", s_d.buf[8:12])[0]

                        s_d.buf[0:4] = struct.pack('i', WorkState.WS_FREE)
                        task_queue2.put((request_id,worker_id,seq_id, p_result))
                if not Flag_step:
                    p_result = self.get_real_data(s_d.buf)
                    worker_id = struct.unpack("i", s_d.buf[4:8])[0]
                    seq_id = struct.unpack("i", s_d.buf[8:12])[0]

                    s_d.buf[0:4] = struct.pack('i',WorkState.WS_FREE)
                    task_queue2.put((request_id,worker_id,seq_id,p_result))
                else:
                    s_d.buf[0:4] = struct.pack('i', WorkState.WS_FREE)

                if self._is_log_time:
                    deata = datetime.now() - start_t
                    micros = deata.seconds * 1000 + deata.microseconds / 1000
                    logger.info('manager workerId {} , runtime {}'.format(sel_id, micros))
        except Exception as e:
            print(e)
        self.release()

class SHM_woker(Process):
    def __init__(self,
                 evt_quit,
                 semaphore,
                 shm_name,
                 shm_size,
                 is_log_time,
                 idx,
                 group_name,
                 daemon=False):
        super().__init__(daemon=daemon)

        self._evt_quit = evt_quit
        self._semaphore= semaphore
        self._idx = idx
        self._group_name = group_name
        self._shm_name = shm_name

        self._s_data = C_sharedata(name=shm_name, create=True, size=shm_size)
        self._evt_signal = multiprocessing.Manager().Event()
        self._is_log_time = is_log_time

    def get_signal(self):
        return self._evt_signal

    def run_begin(self):
        raise NotImplementedError

    def run_end(self):
        raise NotImplementedError

    def run_once(self,request_data):
        raise NotImplementedError

    def release(self):
        if not getattr(self, '__is_closed', False):
            self._evt_signal.set()
            self._evt_quit.set()
            setattr(self, '__is_closed', True)

    def run(self):
        self.run_begin()
        s_data = self._s_data
        try:
            while True :
                self._evt_signal.wait()
                if self._evt_quit.is_set():
                    break
                self._semaphore.acquire()
                flag = struct.unpack("i", s_data.buf[0:4])[0]
                if flag != WorkState.WS_REQUEST:
                    self._semaphore.release()
                    continue
                self._evt_signal.clear()

                s_data.buf[0:4] = struct.pack('i',WorkState.WS_RECIEVE)
                self._semaphore.release()

                # s_data.buf[8:12] = struct.pack('i',0)

                msg_size = struct.unpack("i", s_data.buf[12:16])[0]
                msg = s_data.buf[16:16 + msg_size]
                request_data = pickle.loads(msg)
                start_t = datetime.now()
                XX = self.run_once(request_data)
                seq_id = 0
                if isinstance(XX, typing.Generator):
                    for X in XX:
                        seq_id += 1
                        X = pickle.dumps(X)
                        s_data.buf[4:8] = struct.pack('i', self._idx)
                        s_data.buf[8:12] = struct.pack('i', seq_id)
                        s_data.buf[12:16] = struct.pack("i", len(X))
                        s_data.buf[16:16 + len(X)] = X
                        s_data.buf[0:4] = struct.pack("i", WorkState.WS_FINISH_STEP)
                        while struct.unpack("i", s_data.buf[0:4])[0] != WorkState.WS_FREE:
                            continue
                else:
                    X = pickle.dumps(XX)
                    s_data.buf[4:8] = struct.pack('i', self._idx)
                    s_data.buf[8:12] = struct.pack('i', seq_id)
                    s_data.buf[12:16] = struct.pack("i", len(X))
                    s_data.buf[16:16 + len(X)] = X
                    s_data.buf[0:4] = struct.pack("i", WorkState.WS_FINISH)

                if self._is_log_time:
                    deata = datetime.now() - start_t
                    micros = deata.seconds * 1000 + deata.microseconds / 1000
                    logger.info('worker msg_size {} , runtime {}'.format(msg_size,micros))
        except Exception as e:
            traceback.print_exc()
            logger.error(e)
        del s_data
        self.run_end()
        self.release()