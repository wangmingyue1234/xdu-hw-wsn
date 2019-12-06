import logging
import os
import shutil
import threading
import time
from typing import Any, Dict, List, Optional

import matplotlib

try:
    matplotlib.use('Qt5Agg')
    from matplotlib import pyplot, animation
except ImportError:
    matplotlib.use('TkAgg')
    from matplotlib import pyplot, animation

from wsn import Wsn, WsnNode
from utils import get_log_file_dir_path


class Bystander(object):
    """旁观者
    以上帝视角观察无线传感网络，用适当的方法将其可视化
    """
    # 配置日志
    logger: logging.Logger = logging.getLogger('bystander')

    wsn: Wsn
    thread: Optional[threading.Thread]
    thread_cnt: str
    frames_log: List[List[Dict[str, Any]]]

    last_status: Optional[List[Dict[str, Any]]]
    fig: pyplot.Figure
    ax: pyplot.Axes

    def __init__(self, wsn: Wsn):
        self.wsn = wsn
        self.thread = None
        self.thread_cnt = 'stop'
        self.frames_log = []

    def start(self) -> bool:
        """开始旁观
        在一个子线程中持续监视无线传感网，如果已经在运行不会重启
        :return: 如果线程启动成功则返回 True ，否则返回 False
        """
        if self.thread is not None and self.thread.is_alive():
            return True

        self.thread_cnt = 'start'
        self.thread = threading.Thread(target=self.thread_main, name='bystander')
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
        """旁观者线程的主函数
        """
        self.logger.info('旁观者启动')
        self.init()

        while True:
            if self.thread_cnt == 'stop':
                self.close()
                self.logger.info('旁观者停止')
                break

            self.action()
            time.sleep(0.2)

    def init(self):
        self.last_status = None
        self.fig, self.ax = pyplot.subplots()
        self.ax.set_aspect('equal')

        # 开启交互模式
        pyplot.ion()

    def close(self):
        pyplot.close(self.fig)
        # 关闭交互模式
        pyplot.ioff()

        self.generate_anim()

    def action(self):
        status = []
        for node in self.wsn.node_manager.nodes:
            status.append(self.extract_node_info(node))

        if status != self.last_status:
            # 网络发生变化，画图
            self.frames_log.append(status)
            self.logger.info('更新图像')
            self.draw_nodes(self.fig, self.ax, status)

            self.last_status = status
            pyplot.pause(0.001)

    def generate_anim(self):
        """生成动画
        生成动画并且保存成 gif 和 html
        """
        self.logger.info('正在生成动画...')
        fig, ax = pyplot.subplots()

        def init():
            ax.set_aspect(1)
            return []

        def update(frame: int) -> List[pyplot.Artist]:
            self.reset_figure(fig, ax)

            artists = []

            for node_info in self.frames_log[frame]:
                artists.extend(self.draw_node(ax, node_info))

            return artists

        anim = animation.FuncAnimation(
            fig, update,
            frames=len(self.frames_log),
            init_func=init,
            blit=True,
            interval=500
        )

        # 保存动画
        if 'imagemagick' in animation.writers.avail:
            self.logger.info('正在将动画导出到 result.gif')
            anim.save(f'{get_log_file_dir_path()}/result.gif', writer='imagemagick')
        else:
            self.logger.warning('不支持保存成 gif')

        os.makedirs(f'{get_log_file_dir_path()}/result/')
        self.logger.info('正在将动画导出到 result/index.html')
        anim.save(f'index.html', writer='html')
        shutil.move('index_frames', f'{get_log_file_dir_path()}/result/')
        shutil.move('index.html', f'{get_log_file_dir_path()}/result/')
        anim.to_jshtml()

        pyplot.close(fig)
        self.logger.info('动画导出完成...')

    def draw_nodes(self, fig: pyplot.Figure, ax: pyplot.Axes, nodes_info: List[Dict[str, Any]]) -> None:
        self.reset_figure(fig, ax)

        for node_info in nodes_info:
            self.draw_node(ax, node_info)

    def extract_node_info(self, node: WsnNode) -> Dict[str, Any]:
        """从一个节点提取出与画出节点有关的信息
        """
        node_info = {
            'node_id': node.node_id,
            'xy': node.xy,
            'r': node.r,
            'power': node.power,
            'total_power': node.total_power,
            'label': '',
            'color': '',
            'last_node':
                self.wsn.node_manager.nodes[int(max(node.route_len['1'].items(), key=lambda x: x[1])[0])-1].xy
                if node.route_len.get('1') else None
        }

        if node.node_id == 1:
            node_info['label'] = 'source'
            node_info['color'] = 'red'
        elif not node.is_alive:
            node_info['label'] = 'dead'
            node_info['color'] = 'black'
        elif node.sending or node.send_queue or node.reply_queue:
            node_info['label'] = 'sending'
            node_info['color'] = 'blue'
        elif node.node_id in self.wsn.node_manager.nodes[0].replied_nodes:
            node_info['label'] = 'replied'
            node_info['color'] = 'yellow'
        elif node.recv_count > 0:
            node_info['label'] = 'received'
            node_info['color'] = 'orange'
        else:
            node_info['label'] = 'alive'
            node_info['color'] = 'green'

        return node_info

    @staticmethod
    def reset_figure(fig: pyplot.Figure, ax: pyplot.Axes) -> None:
        """清空并重置一个画布
        """
        fig.gca().cla()
        fig.gca().set_title('Wireless Sensor Networks')
        fig.gca().set_xlabel('x')
        fig.gca().set_ylabel('y')
        fig.set_size_inches(8, 6)
        ax.set_position((0.1, 0.11, 0.6, 0.8))

        legend_elements = (
            pyplot.Line2D(xdata=[], ydata=[], marker='.', linewidth=0, color='red', label='source'),
            pyplot.Line2D(xdata=[], ydata=[], marker='.', linewidth=0, color='green', label='alive'),
            pyplot.Line2D(xdata=[], ydata=[], marker='.', linewidth=0, color='orange', label='received'),
            pyplot.Line2D(xdata=[], ydata=[], marker='.', linewidth=0, color='yellow', label='replied'),
            pyplot.Line2D(xdata=[], ydata=[], marker='.', linewidth=0, color='blue', label='sending'),
            pyplot.Line2D(xdata=[], ydata=[], marker='.', linewidth=0, color='black', label='dead'),
            pyplot.Circle(xy=(0, 0), radius=0, alpha=0.4, color='red', label='range of signal\n(source node)'),
            pyplot.Circle(xy=(0, 0), radius=0, alpha=0.4, color='green', label='range of signal\n(alive node)'),
            pyplot.Circle(xy=(0, 0), radius=0, alpha=0.4, color='orange', label='range of signal\n(received node)'),
            pyplot.Circle(xy=(0, 0), radius=0, alpha=0.4, color='yellow', label='range of signal\n(replied node)'),
            pyplot.Circle(xy=(0, 0), radius=0, alpha=0.4, color='blue', label='range of signal\n(sending node)'),
        )
        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0)

    @staticmethod
    def draw_node(ax: pyplot.Axes, node_info: Dict[str, Any]) -> List[pyplot.Artist]:
        """根据一个节点的信息画出一个节点
        """
        artists = []

        artists.extend(ax.plot(node_info['xy'][0], node_info['xy'][1], '.', color=node_info['color']))
        if node_info['label'] not in ('dead', ):
            cir = pyplot.Circle(
                xy=node_info['xy'],
                radius=node_info['r'],
                alpha=node_info['power'] / node_info['total_power'] * 0.1,
                color=node_info['color']
            )
            ax.add_artist(cir)
            artists.append(cir)
            if node_info['last_node']:
                artists.extend(ax.plot(
                    [node_info['xy'][0], node_info['last_node'][0]],
                    [node_info['xy'][1], node_info['last_node'][1]],
                    marker='_', linewidth=1, alpha=0.2, color='red'
                ))

        return artists
