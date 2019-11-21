import logging
import os
import sys
import time


log_file_dir_path = './log'
if not os.path.exists(log_file_dir_path):
    os.makedirs(log_file_dir_path)


if not os.environ.get('PY_LAUNCH_TIME'):
    os.environ['PY_LAUNCH_TIME'] = time.strftime('%Y-%m-%d_%H%M%S')
run_time = os.environ.get('PY_LAUNCH_TIME')


def get_logger(log_module_name: str) -> logging.Logger:

    logger = logging.getLogger(log_module_name)

    formatter = logging.Formatter(f'[%(asctime)s %(levelname)-8s][{logger.name}] %(message)s')

    file_handler = logging.FileHandler(f'{log_file_dir_path}/{run_time}.log', encoding='utf-8')
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

    return logger
