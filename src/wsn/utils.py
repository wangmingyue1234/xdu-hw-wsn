import logging

import numpy

from .core import Wsn


# 日志配置
logger: logging.Logger = logging.getLogger('wsn.utils')


def generate_rand_nodes(
        wsn: Wsn,
        wsn_width_x: float, wsn_width_y: float, node_num: int,
        node_r_mu: float, node_r_sigma: float, node_power: float, node_pc_per_send
) -> Wsn:
    """生成随机节点
    根据实验参数，生成所需的随机节点

    :param wsn: 需要生成节点的无线传感网络
    :param wsn_width_x: 无线传感网总宽度
    :param wsn_width_y: 无线传感网总长度
    :param node_num: 需要生成的节点数目
    :param node_r_mu: 节点通信半径 r 的均值 μ
    :param node_r_sigma: 节点通信半径 r 的标准差 σ
    :param node_power: 节点初始总电量
    :param node_pc_per_send: 节点单次发射耗电量
    :return: 输入参数 `wsn`
    """
    node_num = node_num if node_num >= 0. else 0.
    node_pc_per_send = node_pc_per_send if node_pc_per_send >= 0. else 0.
    node_power = node_power if node_power >= 0. else 0.
    node_r_sigma = node_r_sigma if node_r_sigma >= 0. else 0.

    # 设置随机数种子
    numpy.random.seed(int(time.time()))
    # 实验报告中例子使用的随机数种子
    # numpy.random.seed(64540)

    for _ in range(node_num):
        # 通信半径是正态分布的随机值（的绝对值）
        r = abs(numpy.random.normal(node_r_mu, node_r_sigma))

        # 坐标是平均分布的随机值
        x = numpy.random.uniform(0, wsn_width_x)
        y = numpy.random.uniform(0, wsn_width_y)

        wsn.node_manager.add_node(x, y, r, node_power, node_pc_per_send)

    return wsn
