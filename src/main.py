import logging
import threading

from utils import init_root_logger, Scheduler, EnumScheduleMode, TerminationCondition
from bystander import Bystander
from wsn import Wsn
from wsn.utils import generate_rand_nodes


# 初始化日志配置
init_root_logger()
logger: logging.Logger = logging.getLogger('main')


def main(multithreading: bool = True):
    node_num = 300

    logger.info('正在生成无线传感网络...')
    wsn = generate_rand_nodes(
        wsn=Wsn(), wsn_width_x=100, wsn_width_y=100,
        node_num=node_num, node_r_mu=10, node_r_sigma=5, node_power=100000000000, node_pc_per_send=1
    )
    logger.info('无线传感网络生成完成')

    bystander = Bystander(wsn)
    logger.info('旁观者生成完成')

    # 给一号节点注入灵魂
    wsn.node_manager.nodes[0].teammate_num = node_num * 0.95
    wsn.node_manager.nodes[0].send_queue.append('Hello World!')

    if multithreading:
        Scheduler.schedule(
            bystander, EnumScheduleMode.MULTI_THREAD,
            [
                TerminationCondition.UserDriven(),
                TerminationCondition.NodeDriven(),
                TerminationCondition.RunningTime(300),
                TerminationCondition.SurvivalRate(0.6),
            ]
        )
    else:
        Scheduler.schedule(
            bystander, EnumScheduleMode.SINGLE_THREAD,
            [
                TerminationCondition.UserDriven(),
                TerminationCondition.NodeDriven(),
                TerminationCondition.NumOfCycles(300),
                TerminationCondition.SurvivalRate(0.6),
            ]
        )

    logger.info('正在进行电量统计..')
    power_usage = 0
    for node in wsn.node_manager.nodes:
        power_usage += (node.total_power - node.power)
    logger.warning(f'本次传输总耗电量 {power_usage} 点')
    logger.info('主线程结束...')


if __name__ == '__main__':
    threading.main_thread().setName('main')
    main(False)
