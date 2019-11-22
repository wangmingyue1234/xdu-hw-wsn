import threading
import time
from typing import Optional

import matplotlib
matplotlib.use('GTK3Agg')
from matplotlib import pyplot, animation, figure
# from matplotlib.patches import Circle

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

    def stop(self, timeout: int = -1) -> bool:
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
        status_log = []
        frame_num = 0

        pyplot.ion()
        fig, ax = pyplot.subplots()

        while True:
            frame_num += 1
            if self.thread_cnt == 'stop':
                self.logger.info('bystander.thread: 旁观者停止')
                pyplot.ioff()
                self.generate_gif(status_log)
                break

            status = []

            for node in self.wsn.node_manager.nodes:
                if node.node_id == 1:
                    status.append((node.node_id, node.xy, node.r, node.power, 'source', 'red'))
                    continue
                if not node.is_alive:
                    status.append((node.node_id, node.xy, node.r, node.power, 'dead', 'black'))
                    continue
                if node.recv_count > 0:
                    status.append((node.node_id, node.xy, node.r, node.power, 'received', 'blue'))
                    continue
                status.append((node.node_id, node.xy, node.r, node.power, 'alive', 'green'))

            if status != last_status:
                status_log.append((status, frame_num))
                # 网络发生变化，画图
                self.logger.info('更新图像')
                pyplot.cla()

                pyplot.title('WSN')
                pyplot.xlabel('x')
                pyplot.ylabel('y')
                ax.set_aspect(1)

                for node in status:
                    ax.plot(node[1][0], node[1][1], '.', color=node[5])
                    cir = pyplot.Circle(xy=node[1], radius=node[2], alpha=node[3] / 1000, color=node[5])
                    ax.add_artist(cir)

                # pyplot.legend(loc='upper right')
                pyplot.draw()
                last_status = status
                pyplot.pause(0.2)
            else:
                time.sleep(0.2)

    @staticmethod
    def generate_gif(status_log):
        print(status_log[-1][1])
        fig, ax = pyplot.subplots()

        def init():
            fig.gca().cla()
            ax.set_aspect(1)
            return []

        def update(frame_num):
            fig.gca().cla()
            artists = []
            frame = frame_num[0]

            for node in frame:
                artists.extend(ax.plot(node[1][0], node[1][1], '.', color=node[5]))
                cir = pyplot.Circle(xy=node[1], radius=node[2], alpha=node[3] / 1000, color=node[5])
                ax.add_artist(cir)
                if cir:
                    artists.append(cir)
            return artists

        anim = animation.FuncAnimation(fig, update, frames=status_log, init_func=init, blit=True, interval=500)
        anim.save('hhh.gif', writer='imagemagick')
        pyplot.show()
