import logging
import os
import sys
import time


# 记录第一次引入该模块时的系统时间，用于作为日志文件和路径名
launch_time: str = time.strftime('%Y-%m-%d_%H%M%S')


def get_log_file_dir_path() -> str:
    """获取存放日志的根目录
    该目录为启动脚本时工作路径下的 ./log/ 目录下以本次运行的启动时间命名的目录
    """
    log_file_dir_path = os.path.abspath(f'./log/{launch_time}')
    if not os.path.exists(log_file_dir_path):
        os.makedirs(log_file_dir_path)
    return log_file_dir_path


def init_root_logger() -> None:
    """初始化根日志配置
    """
    # 日志根目录
    log_file_dir_path = get_log_file_dir_path()

    fmt = '[%(asctime)s,%(msecs)03d][%(levelname)-8s][%(name)-9s] %(threadName)-9s: %(message)s'
    datefmt = '%H:%M:%S'
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    file_handler = logging.FileHandler(f'{log_file_dir_path}/{launch_time}.log', encoding='utf-8')
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # 根日志设置
    root_logger = logging.getLogger()

    # 保存日志到文件
    root_logger.addHandler(file_handler)

    # 打印日志到终端
    try:
        # 在终端打印彩色的 log
        import coloredlogs
        coloredlogs.install(
            fmt=fmt,
            datefmt=datefmt,
            logger=root_logger
        )
    except ImportError:
        # 以下两句只是为了避免告警
        coloredlogs = None
        _ = coloredlogs

        # 没有 coloredlogs 就打印单色的 log
        root_logger.addHandler(console_handler)

    root_logger.setLevel(logging.INFO)
