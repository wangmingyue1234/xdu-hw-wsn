from typing import List


class BaseMessage(object):
    """基础消息（所有其它消息的基类）
    最简单的消息，除了“消息内容”没有其它任何信息
    """
    # 消息内容
    data: str

    def __init__(self, data: str = ''):
        """
        :param data: 消息内容
        """
        self.data = data


class NormalMessage(BaseMessage):
    """普通消息
    比基础消息多了“消息经手人”这一信息
    """
    # 消息经手人（的 node_id 的列表）
    handlers: List[int]

    def __init__(self, data: str = '', source: int = 0):
        """
        :param data: 消息内容
        :param source: 源头发送者
        """
        super(NormalMessage, self).__init__(data)
        self.handlers = [source, ]

    def handle(self, node_id: int = 0) -> None:
        """记录一个经手人
        :param node_id: 经手人的 node_id
        """
        self.handlers.append(node_id)

    @property
    def source(self):
        return self.handlers[0]
