import threading
import time

from utils import get_logger
from bystander import Bystander
from wsn import Wsn
from wsn.utils import generate_rand_nodes


# 日志配置
logger = get_logger('main')


def main():
    logger.info('正在生成无线传感网络...')
    wsn = generate_rand_nodes(
        wsn=Wsn(), wsn_width_x=100, wsn_width_y=100,
        node_num=300, node_r_mu=10, node_r_sigma=5, node_power=100, node_pc_per_send=0
    )
    logger.info('无线传感网络生成完成')

    bystander = Bystander(wsn)
    logger.info('旁观者生成完成')

    logger.info('正在启动旁观者..')
    if bystander.start():
        logger.info('旁观者启动成功')
    else:
        logger.error('旁观者启动失败')
        exit(-1)

    logger.info('正在启动无线传感网..')
    if wsn.start_all():
        logger.info('无线传感网启动成功')
    else:
        logger.error('无线传感网启动，部分节点失败')
        exit(-1)

    time.sleep(30)

    logger.info('正在停止无线传感网..')
    if wsn.stop_all():
        logger.info('无线传感网停止成功')
    else:
        logger.error('无线传感网停止，部分节点失败')

    time.sleep(2)

    logger.info('正在停止旁观者..')
    if bystander.stop(30):
        logger.info('旁观者停止成功')
    else:
        logger.error('旁观者停止失败')

    logger.info('主线程执行完毕，等待所有子线程结束...')


if __name__ == '__main__':
    main()
