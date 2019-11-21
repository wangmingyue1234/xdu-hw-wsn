import threading
import time
from typing import Optional

from matplotlib import pyplot
from matplotlib.patches import Circle

from utils import get_logger
from wsn import Wsn


class Bystander(object):
    """旁观者
    以上帝视角观察无线传感网络，用适当的方法将其可视化
    """
    # 配置日志
    logger = get_logger('bystander')

    wsn: Wsn
    thread: Optional[threading.Thread]
    thread_cnt: str

    def __init__(self, wsn: Wsn):
        self.wsn = wsn
        self.thread = None
        self.thread_cnt = 'stop'

    def start(self) -> bool:
        """开始旁观
        在一个子线程中持续监视无线传感网，如果已经在运行不会重启
        :return: 如果线程启动成功则返回 True ，否则返回 False
        """
        if self.thread is not None and self.thread.is_alive():
            return True

        self.thread_cnt = 'start'
        self.thread = threading.Thread(target=self.thread_main)
        self.thread.start()

        return self.thread.is_alive()

    def stop(self, timeout: int) -> bool:
        """停止旁观
        :param timeout: 等待线程结束的超时时间（秒），如果 < 0 则不等待（函数一定返回 True ），如果 0 则表示无限长的超时时间
        :return: 只要方法执行完线程是处于停止状态，就返回 True 否则返回 False
        """
        if self.thread is None or not self.thread.is_alive():
            self.logger.info(f'已通知旁观者停止，但不等待其停止')
            return True

        # 设置控制位，通知线程应当停止
        self.thread_cnt = 'stop'

        if timeout < 0:
            self.logger.info('已通知旁观者停止，但不等待其停止')
            return True

        try:
            # 等待线程停止，超时时间 30 秒
            self.logger.error(f'等待旁观者结束，超时时间 {timeout} 秒')
            self.thread.join(timeout)
            self.thread = None
        except TimeoutError:
            self.logger.error('等待旁观者结束超时')

        # 判定停止结果
        if self.thread is None or self.thread.is_alive():
            self.logger.info('旁观者已停止')
            return True
        else:
            self.logger.warning('旁观者停止失败')
            return False

    def thread_main(self):
        self.logger.info('bystander.thread: 旁观者启动')
        last_status = None

        pyplot.ion()
        fig = pyplot.figure()
        ax = fig.add_subplot()

        while True:
            if self.thread_cnt == 'stop':
                self.logger.info('bystander.thread: 旁观者停止')
                pyplot.ioff()
                # pyplot.show()
                break

            status = []

            for node in self.wsn.node_manager.nodes:
                if not node.is_alive:
                    status.append((node.node_id, node.xy, node.r, 'dead'))
                    continue
                if node.recv_count > 0:
                    status.append((node.node_id, node.xy, node.r, 'received'))
                    continue
                status.append((node.node_id, node.xy, node.r, 'alive'))

            if status != last_status:
                # 网络发生变化，画图
                self.logger.info('更新图像')
                pyplot.cla()

                pyplot.title('WSN')
                pyplot.xlabel('x')
                pyplot.ylabel('y')
                ax.set_aspect(1)

                for node in status:

                    if node[0] == 1:
                        color = 'red'
                    elif node[3] == 'dead':
                        color = 'black'
                    elif node[3] == 'received':
                        color = 'blue'
                    elif node[3] == 'alive':
                        color = 'green'
                    else:
                        color = 'black'

                    ax.plot(node[1][0], node[1][1], '.', color=color)
                    cir = Circle(xy=node[1], radius=node[2], alpha=0.1, color=color)
                    ax.add_patch(cir)

                # pyplot.legend(loc='upper right')

                last_status = status

            pyplot.pause(0.2)
