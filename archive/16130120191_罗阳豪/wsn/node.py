import logging
import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Tuple, Optional, Set

from utils import node_want_to_terminate

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

    # 收发消息相关
    recv_queue: List[NormalMessage]
    send_queue: List[str or NormalMessage]
    reply_queue: Dict[str, NormalMessage]
    recv_count: int
    replied_nodes: Set[int or str]
    sending: Optional[NormalMessage]
    teammate_num: int
    route_len: Dict[str, Dict[str, int]]
    partners: List[str]
    action: Callable[..., Any]
    replied_messages: Set[str]

    # 是否多线程模式
    multithreading: bool = True

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
        self.send_queue = []
        self.reply_queue = dict()
        self.recv_count = 0
        self.replied_nodes = set()
        self.sending = None
        self.medium = medium
        self.action = self.action2
        self.route_len = {}
        self.teammate_num = 0
        self.replied_messages = set()

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
        node_tag = ("node-" + str(self.node_id) + ": ") if not self.multithreading else ""

        if self.power - self.pc_per_send >= 0:
            self.power -= self.pc_per_send
            self.medium.spread(self, message)
            self.logger.info(f'{node_tag}发送消息 "{message.data}"')
        else:
            self.stop()
            self.logger.warning(f'{node_tag}电量不足，发送失败，已关机')

    def thread_main(self) -> None:
        self.logger.info(f'节点启动')
        while True:
            if self.thread_cnt == 'stop':
                self.logger.info(f'节点停止')
                break
            self.action()
            time.sleep(5)

    def action0(self):
        """无限复读广播
        """
        node_tag = ("node-" + str(self.node_id) + ": ") if not self.multithreading else ""

        # 如果发送队列里有消息需要发送，且当前没有别的消息需要发送，则从发送队列取出一条消息进行发送
        if self.send_queue and self.sending is None:
            message = self.send_queue.pop(0)
            if isinstance(message, str):
                self.sending = NormalMessage(data=message, source=self.node_id)
            elif isinstance(message, NormalMessage):
                self.sending = message

        # 如果当前有正在发送的消息则发送之
        if self.sending is not None:
            self.send(NormalMessage(uuid=self.sending.uuid, data=self.sending.data, source=self.node_id))

        # 处理收到的各种消息
        while self.recv_queue:
            message = self.recv_queue.pop(0)
            if message.uuid == self.sending:
                continue

            self.recv_count += 1
            self.logger.info(f'{node_tag}接收到消息 "{message.data}"')

            self.sending = message

    def action1(self) -> Optional[bool]:
        """要求回应
        """
        node_tag = ("node-" + str(self.node_id) + ": ") if not self.multithreading else ""

        # 如果一条消息已经被全部确认，则该条消息发送完毕
        if self.sending is not None and len(self.replied_nodes) >= self.teammate_num:
            self.sending = None
            self.replied_nodes = set()
            # 唤醒主线程
            if self.multithreading:
                self.logger.info(f'唤起主线程')
                node_want_to_terminate.set()
            else:
                return True

        # 如果发送队列里有消息需要发送，且当前没有别的消息需要发送，则从发送队列取出一条消息进行发送
        if self.send_queue and self.sending is None:
            message = self.send_queue.pop(0)
            if isinstance(message, str):
                self.sending = NormalMessage(data=message, source=self.node_id)
            elif isinstance(message, NormalMessage):
                self.sending = message

        # 如果当前有正在发送的消息则发送之
        if self.sending is not None:
            self.send(self.sending)

        # 处理收到的各种消息
        recv_set = set()
        while self.recv_queue:
            message = self.recv_queue.pop(0)
            # 自己发送的或者处理过的消息丢弃
            if self.node_id in message.handlers:
                if self.sending is not None and message.uuid == self.sending.uuid and message.is_reply:
                    self.replied_nodes.add(message.handlers[0])
                continue

            if f'{message.uuid}-{message.handlers[0]}-{message.handlers[-1]}' not in recv_set:
                recv_set.add(f'{message.uuid}-{message.handlers[0]}-{message.handlers[-1]}')

                if not message.is_reply:
                    self.recv_count += 1
                    self.logger.info(f'{node_tag}接收到消息 "{message.data}"')

                # 给消息注册上自己名字，转发之
                message.register(self.node_id)
                self.send(message)

                # 如果消息不是一个回应，则同时发送一条对该消息的回应
                if not message.is_reply:
                    self.send(NormalMessage(uuid=message.uuid, is_reply=True, data=message.data, source=self.node_id))

    def action2(self) -> Optional[bool]:
        """要求回应，最常用路径，原路回应
        """
        node_tag = ("node-" + str(self.node_id) + ": ") if not self.multithreading else ""

        # 如果一条消息已经被全部确认，则该条消息发送完毕
        if self.sending is not None and not self.sending.is_reply and len(self.replied_nodes) >= self.teammate_num:
            self.sending = None
            self.replied_nodes = set()
            # 唤醒主线程
            if self.multithreading:
                self.logger.info(f'唤起主线程')
                node_want_to_terminate.set()
            else:
                return True

        # 如果发送队列里有消息需要发送，且当前没有别的消息需要发送，则从发送队列取出一条消息进行发送
        if self.send_queue and self.sending is None:
            message = self.send_queue.pop(0)
            if isinstance(message, str):
                self.sending = NormalMessage(data=message, source=self.node_id)
            elif isinstance(message, NormalMessage):
                self.sending = message

        # 如果当前有正在发送的消息则发送之
        if self.sending is not None:
            self.send(self.sending)
        for i, reply in self.reply_queue.items():
            for _ in range(1):
                self.send(reply)

        # 处理收到的各种消息
        while self.recv_queue:
            message = self.recv_queue.pop(0)

            if message.is_reply:

                self.logger.info(f'{node_tag}接收到消息 "{message.data}" {message.handlers}')
                if self.reply_queue.get(f'{message.uuid}-{message.handlers[0]}') is not None and \
                        len(
                            self.reply_queue.get(f'{message.uuid}-{message.handlers[0]}').handlers
                        ) > len(message.handlers):
                    self.reply_queue.pop(f'{message.uuid}-{message.handlers[0]}')
                    continue

                if len(message.handlers) < 2:
                    continue

                if self.node_id != message.handlers[1]:
                    continue

                message.handlers.pop(1)
                self.send(message)

                if self.sending is not None and not self.sending.is_reply and message.uuid == self.sending.uuid:
                    self.replied_nodes.add(message.handlers[0])
                    continue

                if f'{message.uuid}-{message.handlers[0]}' not in self.replied_messages:
                    self.replied_messages.add(f'{message.uuid}-{message.handlers[0]}')
                    self.reply_queue[f'{message.uuid}-{message.handlers[0]}'] = message

            else:
                # 自己发送的或者处理过的消息丢弃
                if self.node_id in message.handlers:
                    continue

                self.recv_count += 1
                self.logger.info(f'{node_tag}接收到消息 "{message.data}" {message.handlers}')

                if str(message.handlers[0]) not in self.route_len.keys():
                    self.route_len[str(message.handlers[0])] = {}
                start_point_route = self.route_len[str(message.handlers[0])]
                if str(message.handlers[-1]) not in start_point_route.keys():
                    start_point_route[str(message.handlers[-1])] = 0
                start_point_route[str(message.handlers[-1])] += 1

                # 是从最常见路径传播过来的
                if start_point_route[str(message.handlers[-1])] == max(*list(start_point_route.values()) + [0]):
                    # 给消息注册上自己名字，转发之
                    message.register(self.node_id)
                    self.send(message)

                    # 没回复过的消息回应以下
                    if message.uuid not in self.replied_messages:
                        message.is_reply = True
                        message.handlers = message.handlers[::-1]
                        self.replied_messages.add(message.uuid)
                        self.reply_queue[f'{message.uuid}-{message.handlers[0]}'] = message

    def action3(self):
        """节点一次活动（方案二）
        在多线程模式时，该函数每隔一段休眠时间运行一次
        在单线程模式，由调度器调度运行
        """
        node_tag = ("node-" + str(self.node_id) + ": ") if not self.multithreading else ""

        # 如果发送队列里有消息需要发送，且当前没有别的消息需要发送，则从发送队列取出一条消息进行发送
        if self.send_queue and self.sending is None:
            message = self.send_queue.pop(0)
            if isinstance(message, str):
                self.sending = NormalMessage(data=message, source=self.node_id)
                self.replied_nodes.add(self.node_id)
            elif isinstance(message, NormalMessage):
                self.sending = message

        # 如果当前有正在发送的消息则发送之
        if self.sending is not None:
            for _ in range(100):
                self.send(self.sending)
            self.sending = None

        # 处理收到的各种消息
        while self.recv_queue:
            message = self.recv_queue.pop(0)
            # 自己发送的或者处理过的消息丢弃
            if message.uuid in self.replied_nodes:
                continue

            self.recv_count += 1
            self.replied_nodes.add(message.uuid)
            self.logger.info(f'{node_tag}接收到消息 "{message.data}"')

            self.send_queue.append(message)

    @property
    def xy(self) -> Tuple[float, float]:
        return self.x, self.y

    @property
    def is_alive(self):
        return not self.multithreading or (self.thread is not None and self.thread.is_alive())


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
