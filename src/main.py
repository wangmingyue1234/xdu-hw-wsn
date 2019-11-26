import logging
import threading

from utils import init_root_logger, main_thread_wakeup
from bystander import Bystander
from wsn import Wsn
from wsn.utils import generate_rand_nodes, schedule


# 初始化日志配置
init_root_logger()
logger: logging.Logger = logging.getLogger('main')


def main(multithreading: bool = True):
    node_num = 100

    logger.info('正在生成无线传感网络...')
    wsn = generate_rand_nodes(
        wsn=Wsn(), wsn_width_x=100, wsn_width_y=100,
        node_num=node_num, node_r_mu=20, node_r_sigma=5, node_power=100000, node_pc_per_send=1
    )
    logger.info('无线传感网络生成完成')

    bystander = Bystander(wsn)
    logger.info('旁观者生成完成')

    if multithreading:
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

    # 给一号节点注入灵魂
    wsn.node_manager.nodes[0].teammate_num = node_num * 0.9
    wsn.node_manager.nodes[0].send_queue.append('Hello World!')

    if multithreading:
        logger.info('主线程挂起，等待事件 main_thread_wakeup ...')
        main_thread_wakeup.clear()
        main_thread_wakeup.wait()
        main_thread_wakeup.clear()

        logger.info('正在停止旁观者..')
        if bystander.stop():
            logger.info('旁观者停止成功')
        else:
            logger.error('旁观者停止失败')

        logger.info('正在停止无线传感网..')
        if wsn.stop_all():
            logger.info('无线传感网停止成功')
        else:
            logger.error('无线传感网停止，部分节点失败')

        logger.info('等待所有子线程结束...')
        for thread in threading.enumerate():
            if thread != threading.currentThread():
                thread.join()
    else:
        # 以单线程模式调度运行
        schedule(bystander)

    logger.info('正在进行电量统计..')
    power_usage = 0
    for node in wsn.node_manager.nodes:
        power_usage += (node.total_power - node.power)
    logger.info(f'本次传输总耗电量 {power_usage} 点')
    logger.info('主线程结束...')


if __name__ == '__main__':
    threading.main_thread().setName('main')
    main()
