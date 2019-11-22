import logging
from functools import reduce
from operator import and_
from typing import List

from .node import WsnNodeManager
from .medium import WsnMedium


class Wsn(object):
    """无线传感网络
    """
    # 日志配置
    logger: logging.Logger = logging.getLogger('wsn.core')

    node_manager: WsnNodeManager
    medium: WsnMedium

    def __init__(self):
        self.medium = WsnMedium(self)
        self.logger.info('初始化通信介质完成')
        self.node_manager = WsnNodeManager(self)
        self.logger.info('初始化节点管理器完成')

    def start_all(self) -> bool:
        """启动所有节点
        启动 node_manager 中管理的所有节点
        如果一个节点已经被启动，不会被重启
        :return: 如果全部启动成功，则返回 True ，否则返回 False
        """
        res: List[bool] = [True, ]
        for node in self.node_manager.nodes:
            res.append(node.start())
        return reduce(and_, res)

    def stop_all(self) -> bool:
        """停止所有节点
        停止 node_manager 中管理的所有节点
        如果一个节点已经停止，则跳过
        :return: 如果全部停止成功，则返回 True ，否则返回 False
        """
        res: List[bool] = [True, ]
        for node in self.node_manager.nodes:
            res.append(node.stop())
        return reduce(and_, res)
