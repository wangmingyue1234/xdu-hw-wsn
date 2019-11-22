import logging
import threading
import time
from enum import Enum
from typing import List, Tuple, Optional

from .message import NormalMessage


class WsnNode(object):
    """无线传感网络中的一个节点
    """
    # 日志配置
    logger: logging.Logger = logging.getLogger('wsn.node')

    class EnumNodeStatus(Enum):
        STOPPED = 0
        RUNNING = 1

    # 节点 id
    node_id: int
    # 节点坐标
    x: float
    y: float
    # 通信参数
    r: float
    power: float
    total_power: float
    pc_per_send: float

    # 节点线程
    thread: Optional[threading.Thread]

    # 节点线程的控制位
    thread_cnt: str

    # 接收消息队列
    recv_queue: List[NormalMessage]
    recv_count: int

    # 用于发送信息的介质
    # medium: WsnMedium

    def __init__(
            self,
            node_id: int, x: float, y: float, r: float,
            total_power: float, pc_per_send: float, medium
    ) -> None:
        self.node_id = node_id
        self.x = x
        self.y = y
        self.r = r
        self.power = total_power
        self.total_power = total_power
        self.pc_per_send = pc_per_send
        self.thread = None
        self.thread_cnt = 'stop'
        self.recv_queue = []
        self.recv_count = 0
        self.medium = medium

    def start(self) -> bool:
        """启动节点
        :return: 只要方法执行完节点是处于运行状态，就返回 True 否则返回 False
        """
        if self.thread is not None and self.thread.is_alive():
            return True

        self.recv_queue = []
        self.recv_count = 0

        self.thread_cnt = 'start'
        self.thread = threading.Thread(target=self.thread_main, name=f'node-{self.node_id}')
        self.thread.start()

        return self.thread.is_alive()

    def stop(self, timeout: int = -1) -> bool:
        """停止节点
        :param timeout: 等待线程结束的超时时间（秒），如果 < 0 则不等待（函数一定返回 True ），如果 0 则表示无限长的超时时间
        :return: 只要方法执行完节点是处于停止状态，就返回 True 否则返回 False
        """
        if self.thread is None or not self.thread.is_alive():
            self.logger.warning(f'node-{self.node_id} 节点已处于停止状态，不能再停止')
            return True

        # 设置控制位，通知线程应当停止
        self.thread_cnt = 'stop'

        if timeout < 0:
            self.logger.info(f'node-{self.node_id} 已通知节点停止，但不等待其停止')
            return True

        try:
            # 等待线程停止，超时时间 30 秒
            self.logger.error(f'node-{self.node_id} 等待线程结束，超时时间 {timeout} 秒')
            self.thread.join(timeout)
            self.thread = None
        except TimeoutError:
            self.logger.error(f'node-{self.node_id} 等待线程结束超时')

        # 判定停止结果
        if self.thread is None or self.thread.is_alive():
            self.logger.info(f'node-{self.node_id} 已停止')
            return True
        else:
            self.logger.warning(f'node-{self.node_id} 停止失败')
            return False

    def echo(self) -> None:
        self.logger.info(f'我还活着！')

    def send(self, message: NormalMessage):
        if self.power - self.pc_per_send >= 0:
            self.power -= self.pc_per_send
            self.medium.spread(self, message)
            self.logger.info(f'发送消息 "{message.data}"')
        else:
            self.stop()
            self.logger.warning(f'电量不足，发送失败，已关机')

    def thread_main(self) -> None:
        self.logger.info(f'节点启动')

        while True:
            if self.thread_cnt == 'stop':
                self.logger.info(f'节点停止')
                break

            if self.node_id == 1:
                # 我是消息源，我要发送消息
                data = 'Hello World!'
                self.send(NormalMessage(data, self.node_id))
            else:

                # 我是其它节点，我要接收消息
                while self.recv_queue:
                    message = self.recv_queue.pop(0)
                    if self.node_id in message.handlers:
                        continue
                    self.recv_count += 1
                    self.logger.info(f'接收到消息 "{message.data}"')
                    message.handle(self.node_id)
                    self.medium.spread(self, message)

            time.sleep(5)

    @property
    def xy(self) -> Tuple[float, float]:
        return self.x, self.y

    @property
    def is_alive(self):
        return self.thread is not None and self.thread.is_alive()


class WsnNodeManager(object):
    """无线传感网络的节点管理器
    为无线传感网络管理节点的生成和销毁
    """
    # 日志配置
    logger: logging = logging.getLogger('wsn.nm')

    nodes: List[WsnNode]
    # wsn: Wsn

    def __init__(self, wsn) -> None:
        self.nodes = []
        self.wsn = wsn

    def add_node(self, x: float, y: float, r: float, power: float, pc_per_send: float) -> WsnNode:

        new_node_id = self.nodes[-1].node_id + 1 if len(self.nodes) > 0 else 1

        new_node = WsnNode(new_node_id, x, y, r, power, pc_per_send, self.wsn.medium)
        self.nodes.append(new_node)

        self.logger.info(f'新增节点 node-{new_node_id} ({x}, {y}), r={r}, power={power}, pc_per_send={pc_per_send}')

        return new_node

    def pop_node(self, node_id: int) -> Optional[WsnNode]:
        try:
            return self.nodes.pop(self.get_nodes_id().index(node_id))
        except ValueError:
            return None

    def get_nodes_id(self) -> List[int]:
        return [node.node_id for node in self.nodes]

    def get_nodes_xy(self, nodes_id: Optional[List[int]] = None) -> List[Tuple[float, float]]:
        nodes_xy = []
        for node in self.nodes if nodes_id is None else [node for node in self.nodes if node.node_id in nodes_id]:
            nodes_xy.append(node.xy)

        return nodes_xy

    @property
    def node_num(self) -> int:
        return len(self.nodes)
