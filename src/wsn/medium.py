import logging
import numpy
import time

from .message import BaseMessage


class WsnMedium(object):
    """无线传感网络的无线信号传播介质
    节点往介质中发送信息，介质给节点传递信息
    介质的“物理特性”决定了一个信息将会送达到哪些节点
    """
    # 配置日志
    logger: logging.Logger = logging.getLogger('wsn.medium')

    # wsn: Wsn

    def __init__(self, wsn):
        self.wsn = wsn

    def spread(self, source_node, message: BaseMessage) -> None:
        # 设置随机数种子
        numpy.random.seed(int(time.time()))

        for target_node in self.wsn.node_manager.nodes:
            # 两节点间距
            d = numpy.linalg.norm(numpy.array(source_node.xy) - numpy.array(target_node.xy))

            # 两节点通信半径
            r1 = source_node.r
            r2 = target_node.r

            # 两节点通信成功概率
            if r1 * r2 <= 0:
                p = 0
            else:
                p = 1 - d * d / r1 / r2

            # 不可能成功的事情就不试了
            if p <= 0:
                continue

            # 上帝掷骰子
            if numpy.random.choice((True, False), p=(p, 1 - p)):
                # 信息传输成功
                target_node.recv_queue.append(message.copy())
            else:
                # 信息传输失败
                continue
