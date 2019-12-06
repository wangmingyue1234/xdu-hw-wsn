import logging
import threading
import time
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy

from bystander import Bystander

from .event import node_want_to_terminate


# 日志配置
logger: logging.Logger = logging.getLogger('scheduler')


class EnumScheduleMode(Enum):
    """调度模式的枚举
    SINGLE_THREAD: 单线程，只有一个主线程，调度器依次调度所有节点和旁观者执行。
                   使用严格轮换法，节点间的调度顺序在每一轮中都会重新随机决定。
    MULTI_THREAD:  多线程，一个节点一个子线程、旁观者一个线程，调度器在主线程做一些管理和控制
    """
    SINGLE_THREAD = 'single_thread'
    MULTI_THREAD = 'multi_thread'


class TerminationCondition(object):
    """终止条件
    定义一些网络终止的条件，用于作为调度器判断是否应该终止网络的依据
    """
    class Ordinary(object):
        """平凡条件
        所有终止条件的基类，实际上这是任何时候都会满足的条件
        对 EnumScheduleMode.SINGLE_THREAD 和 EnumScheduleMode.MULTI_THREAD 模式有效
        """
        pass

    class UserDriven(Ordinary):
        """用户驱动
        用户按下 `Ctrl + C` 引发中断时，该条件满足
        对 EnumScheduleMode.SINGLE_THREAD 和 EnumScheduleMode.MULTI_THREAD 模式有效
        """
        pass

    class NumOfCycles(Ordinary):
        """循环次数
        循环调度指定的次数后，该条件满足
        仅对 EnumScheduleMode.SINGLE_THREAD 模式有效
        """

        num_of_cycles: int

        def __init__(self, num_of_cycles: int):
            if num_of_cycles < 1:
                raise ValueError('网络循环次数不能小于 1')
            self.num_of_cycles = num_of_cycles

    class RunningTime(Ordinary):
        """运行时间
        运行时间达到阈值之后，该条件满足
        仅对 EnumScheduleMode.MULTI_THREAD 模式有效
        """

        running_time_in_seconds: float

        def __init__(self, running_time_in_seconds: float):
            if running_time_in_seconds <= 0:
                raise ValueError('网络运行时间不能小于 0')
            self.running_time_in_seconds = running_time_in_seconds

    class NodeDriven(Ordinary):
        """节点驱动
        如果某节点一次执行后决定要终止，该条件满足
        对 EnumScheduleMode.SINGLE_THREAD 和 EnumScheduleMode.MULTI_THREAD 模式有效
        """
        pass

    class ReceivedRate(Ordinary):
        """接收率
        如果网络中接收到消息的节点占总节点的比率 **不低于** 设定的阈值，该条件满足
        对 EnumScheduleMode.SINGLE_THREAD 和 EnumScheduleMode.MULTI_THREAD 模式有效
        """

        received_rate: float

        def __init__(self, received_rate: float):
            if not 0 <= received_rate <= 1:
                raise ValueError('接收率只能在 [0, 1] 范围内取值')
            self.received_rate = received_rate

    class SurvivalRate(Ordinary):
        """存活率
        如果网络中存活的节点占总节点的比率 **不高于** 设定的阈值，该条件满足
        对 EnumScheduleMode.SINGLE_THREAD 和 EnumScheduleMode.MULTI_THREAD 模式有效
        """

        survival_rate: float

        def __init__(self, survival_rate: float):
            if not 0 <= survival_rate <= 1:
                raise ValueError('存活率只能在 [0, 1] 范围内取值')
            self.survival_rate = survival_rate

    @staticmethod
    def extract(conditions: Optional[List[Ordinary]], mode: EnumScheduleMode) -> Dict[str, Any]:
        conditions_map = {
            'ordinary': False,
            'user_driven': False,
            'num_of_cycles': None,
            'running_time': None,
            'node_driven': False,
            'received_rate': None,
            'survival_rate': None
        }
        if conditions is not None:
            for condition in conditions:

                if type(condition) == TerminationCondition.Ordinary:
                    conditions_map['ordinary'] = True

                elif isinstance(condition, TerminationCondition.UserDriven):
                    conditions_map['user_driven'] = True

                elif isinstance(condition, TerminationCondition.NumOfCycles):
                    if mode == EnumScheduleMode.MULTI_THREAD:
                        logger.warning(f'{type(mode)} 模式下不能使用 {type(condition)} 条件，该条件被跳过')
                        continue
                    if conditions_map['num_of_cycles'] is not None and \
                            conditions_map['num_of_cycles'] != condition.num_of_cycles:
                        raise ValueError(
                            f'设置了两个值不同的 `{type(condition)}` ，值分别是 '
                            f'{conditions_map["num_of_cycles"]} 和 {condition.num_of_cycles}'
                        )
                    conditions_map['num_of_cycles'] = condition.num_of_cycles

                elif isinstance(condition, TerminationCondition.RunningTime):
                    if mode == EnumScheduleMode.SINGLE_THREAD:
                        logger.warning(f'{type(mode)} 模式下不能使用 {type(condition)} 条件，该条件被跳过')
                        continue
                    if conditions_map['running_time'] is not None and \
                            conditions_map['running_time'] != condition.running_time_in_seconds:
                        raise ValueError(
                            f'设置了两个值不同的 `{type(condition)}` ，值分别是 '
                            f'{conditions_map["running_time"]} 和 {condition.running_time_in_seconds}'
                        )
                    conditions_map['running_time'] = condition.running_time_in_seconds

                elif isinstance(condition, TerminationCondition.NodeDriven):
                    conditions_map['node_driven'] = True

                elif isinstance(condition, TerminationCondition.ReceivedRate):
                    if conditions_map['received_rate'] is not None and \
                            conditions_map['received_rate'] != condition.received_rate:
                        raise ValueError(
                            f'设置了两个值不同的 `{type(condition)}` ，值分别是 '
                            f'{conditions_map["received_rate"]} 和 {condition.received_rate}'
                        )
                    conditions_map['received_rate'] = condition.received_rate

                elif isinstance(condition, TerminationCondition.SurvivalRate):
                    if conditions_map['survival_rate'] is not None and \
                            conditions_map['survival_rate'] != condition.survival_rate:
                        raise ValueError(
                            f'设置了两个值不同的 `{type(condition)}` ，值分别是 '
                            f'{conditions_map["survival_rate"]} 和 {condition.survival_rate}'
                        )
                    conditions_map['survival_rate'] = condition.survival_rate

                else:
                    raise ValueError(f'不支持的终止条件 `{type(condition)}`')

        return conditions_map

    @staticmethod
    def check_termination_conditions(
            bystander: Bystander,
            conditions_map: Dict[str, Any],
            mode: EnumScheduleMode,
            num_of_cycles: int = 0,
            running_time: float = 0,
            node_driven: bool = False
    ) -> bool:
        nodes = bystander.wsn.node_manager.nodes

        if conditions_map['ordinary']:
            logger.info(f'凭白无故，触发终止条件 `{TerminationCondition.Ordinary}`')
            return True

        elif mode == EnumScheduleMode.SINGLE_THREAD and conditions_map['num_of_cycles'] and \
                num_of_cycles >= conditions_map['num_of_cycles']:
            logger.info(f'循环调度了 {num_of_cycles} 次，超过阈值 {conditions_map["num_of_cycles"]} ，'
                        f'触发终止条件 `{TerminationCondition.NumOfCycles}`')
            return True

        elif mode == EnumScheduleMode.MULTI_THREAD and conditions_map['running_time'] and \
                running_time >= conditions_map['running_time']:
            logger.info(f'连续运行了 {running_time} 秒，超过阈值 {conditions_map["running_time"]} ，'
                        f'触发终止条件 `{TerminationCondition.NumOfCycles}`')
            return True

        elif conditions_map['node_driven'] and node_driven:
            logger.info(f'节点要求终止，触发终止条件 `{TerminationCondition.NodeDriven}`')
            return True

        elif conditions_map['received_rate'] is not None:
            received_count = 0
            for node in nodes:
                if node.recv_count:
                    received_count += 1
            received_rate = received_count / len(nodes)
            if received_rate >= conditions_map['received_rate']:
                logger.info(f'节点消息接收率 {received_rate} ，高至阈值 {conditions_map["received_rate"]} ，'
                            f'触发终止条件 `{TerminationCondition.ReceivedRate}`')
                return True

        elif conditions_map['survival_rate'] is not None:
            alive_count = 0
            for node in nodes:
                if node.is_alive:
                    alive_count += 1
            survival_rate = alive_count / len(nodes)
            if survival_rate <= conditions_map['survival_rate']:
                logger.info(f'节点存活率 {survival_rate} ，低至阈值 {conditions_map["survival_rate"]} ，'
                            f'触发终止条件 `{TerminationCondition.SurvivalRate}`')
                return True

        return False


class Scheduler(object):
    """调度器
    包装一些节点、旁观者调度和控制方法
    """

    @staticmethod
    def schedule(
            bystander: Bystander,
            mode: EnumScheduleMode = EnumScheduleMode.SINGLE_THREAD,
            termination_conditions: Optional[List[TerminationCondition.Ordinary]] = None,
            rand_seed: Optional[int] = None
    ) -> None:
        """开始调度
        开始调度网络运行，网络运行结束后返回

        :param bystander: 需要调度的网络的旁观者
        :param mode: 调度模式
        :param termination_conditions: 终止条件
        :param rand_seed: 随机数种子（仅 EnumScheduleMode.SINGLE_THREAD 模式有效）
        :return:
        """

        # 整理终止条件
        conditions_map = TerminationCondition.extract(termination_conditions, mode)

        # 单线程模式
        if mode == EnumScheduleMode.SINGLE_THREAD:
            # 设置随机数种子
            numpy.random.seed(int(time.time()) if rand_seed is None else rand_seed)
            return Scheduler.schedule_in_single_thread_mode(bystander, conditions_map)

        # 多线程模式
        elif mode == EnumScheduleMode.MULTI_THREAD:
            return Scheduler.schedule_in_multi_thread_mode(bystander, conditions_map)

        # 其它诡异的模式
        else:
            raise ValueError(f'未知的调度模式 `{mode}`')

    @staticmethod
    def schedule_in_single_thread_mode(bystander: Bystander, conditions_map: Dict[str, Any]) -> None:

        wsn = bystander.wsn
        nodes = wsn.node_manager.nodes

        for node in nodes:
            node.multithreading = False

        # 初始化旁观者
        bystander.init()

        # 初始化终止条件
        node_driven = False
        num_of_cycles = 0

        try:
            while True:

                # 调度每个节点运行一次
                for node in numpy.random.permutation(nodes):
                    if node.action():
                        node_driven = True
                # 调度旁观者运行一次
                bystander.action()

                num_of_cycles += 1

                if TerminationCondition.check_termination_conditions(
                    bystander=bystander,
                    conditions_map=conditions_map,
                    mode=EnumScheduleMode.SINGLE_THREAD,
                    num_of_cycles=num_of_cycles,
                    node_driven=node_driven
                ):
                    break

        except KeyboardInterrupt as e:
            if conditions_map['user_driven']:
                logger.info(f'用户通过按键引发中断，触发终止条件 `{TerminationCondition.UserDriven}`')
            else:
                raise e

        # 关闭旁观者
        bystander.close()

    @staticmethod
    def schedule_in_multi_thread_mode(bystander: Bystander, conditions_map: Dict[str, Any]) -> None:
        wsn = bystander.wsn

        logger.info('正在启动旁观者..')
        if bystander.start():
            logger.info('旁观者启动成功')
        else:
            err = RuntimeError('旁观者启动失败')
            logger.error(err)
            raise err

        logger.info('正在启动无线传感网..')
        if wsn.start_all():
            logger.info('无线传感网启动成功')
        else:
            err = RuntimeError('无线传感网启动，部分节点失败')
            logger.error(err)
            raise err

        # 初始化终止条件
        node_want_to_terminate.clear()
        start_time = time.time()

        try:
            while True:
                time.sleep(5)

                if TerminationCondition.check_termination_conditions(
                    bystander=bystander,
                    conditions_map=conditions_map,
                    mode=EnumScheduleMode.MULTI_THREAD,
                    running_time=time.time() - start_time,
                    node_driven=node_want_to_terminate.is_set()
                ):
                    break

        except KeyboardInterrupt as e:
            if conditions_map['user_driven']:
                logger.info(f'用户通过按键引发中断，触发终止条件 `{TerminationCondition.UserDriven}`')
            else:
                raise e

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
        logger.info('调度器退出')
