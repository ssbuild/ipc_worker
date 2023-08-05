# -*- coding:utf-8 -*-
import setuptools
import sys
import platform
import os
import shutil

from setuptools import Extension,find_packages



def get_desc():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    def load_file(demo_file):
        with open(demo_file,mode='r',encoding='utf-8') as f:
            data_string = str(f.read())
        return data_string

    data_string = 'support share memory (py>=3.8 and linux) and mq process worker (py >=3.6)\n'
    long_description_str = '```py' + '\n' + data_string + '\n' + '```' + '\n'


    data_string = load_file(os.path.join(current_dir,'tests/test_shm_ipc.py'))


    long_description_str += '```py' + '\n' + data_string + '\n'+ '```' + '\n'

    data_string = load_file(os.path.join(current_dir, 'tests/test_zmq_ipc.py'))
    long_description_str += '```py' + '\n' + data_string + '\n' + '```' + '\n'

    return long_description_str

title = 'ipc-worker: Inter-Process Communication , muti Process Woker works by share memory or MQ.'
current_dir = os.path.dirname(os.path.abspath(__file__))
platforms_name = sys.platform + '_' + platform.machine()

if __name__ == '__main__':
    setuptools.setup(
        platforms=platforms_name,
        name="ipc-worker",
        version="0.1.0",
        author="ssbuild",
        author_email="9727464@qq.com",
        description=title,
        long_description_content_type='text/markdown',
        long_description= title + '\n\n' + get_desc(),
        url="https://github.com/ssbuild/ipc_worker",
        package_dir={"": "src"},
        packages=find_packages("src"),
        include_package_data=True,
        package_data={'': ['*.pyd','*.so','*.dat','*.h','*.c','*.java','.__data__.pys','.__meta__.pys']},
        install_requires=["termcolor"],
        python_requires='>=3, <4',
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Intended Audience :: Education',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: Apache Software License',
            'Programming Language :: C++',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
            'Topic :: Scientific/Engineering',
            'Topic :: Scientific/Engineering :: Mathematics',
            'Topic :: Scientific/Engineering :: Artificial Intelligence',
            'Topic :: Software Development',
            'Topic :: Software Development :: Libraries',
            'Topic :: Software Development :: Libraries :: Python Modules',
        ],
        license='Apache 2.0',
        keywords=["ipc-worker","ipc_worker","ipc","process worker","ipc","ipc mq","fast-ipc","process ipc",
                  ],
    )
