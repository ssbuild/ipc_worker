# -*- coding: utf-8 -*-
# @Time    : 2021/11/23 10:03
# @Author  : tk

import os
from termcolor import colored
from multiprocessing import shared_memory, Event, Condition
from ..utils import set_logger

logger = set_logger(colored('VENTILATOR', 'magenta'))

# 进程数据交换协议. 标志状态是否空闲（空闲 为0 ， 由数据请求方置为 1 ， 工作者接收该任务置为 2 ,工作完成处理方式置为 3 ， 数据请求方读取万结果后置为0）
# 数据长度
# 数据内容

class C_sharedata:
    def __init__(self, name, create=True, size=0):
        try:
            self.is_clean = False
            if create:
                self.shm = shared_memory.SharedMemory(name=name, create=create, size=size)
            else:
                self.shm = shared_memory.SharedMemory(name=name)
        except Exception as e:
            try:
                logger.warning('warning {}'.format(e))
                if create:
                    self.shm = shared_memory.SharedMemory(name=name)
                else:
                    self.is_clean = True
            except Exception as e:
                logger.error('SharedMemory except {}'.format(e))
                self.is_clean = True

    def __del__(self):
        self.close()

    def close(self):
        try:
            if not self.is_clean:
                if self.shm is not None:
                    self.shm.close()
                self.is_clean = True
        except Exception as e:
            logger.error('SharedMemory close except {}'.format(e))

    @property
    def buf(self):
        return self.shm.buf


def get_device_num():
    try:
        import GPUtil
        num_all_gpu = len(GPUtil.getGPUs())
        avail_gpu = GPUtil.getAvailable(order='memory', limit=num_all_gpu, maxMemory=0.9, maxLoad=0.9)
        num_avail_gpu = len(avail_gpu)

    except FileNotFoundError:
        num_avail_gpu = 0
        logger.warning('nvidia-smi is missing, often means no gpu on this machine. '
                       'fall back to cpu!')

    logger.info('num_avail_gpu: %d' % num_avail_gpu)
    return num_avail_gpu