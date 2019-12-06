from typing import List
from uuid import uuid4, UUID


class BaseMessage(object):
    """基础消息（所有其它消息的基类）
    最简单的消息，除了 data 没有其它任何属性
    """
    data: str

    def __init__(self, data: str = ''):
        """
        :param data: 消息内容
        """
        self.data = data

    def copy(self):
        return BaseMessage(self.data)


class RegisteredMessage(BaseMessage):
    """记名消息
    比 BaseMessage 多了 handlers 这一属性
    """
    handlers: List[int]

    def __init__(self, data: str = '', source: int = 0):
        """
        :param data: 消息内容
        :param source: 源头发送者
        """
        super(RegisteredMessage, self).__init__(data)
        self.handlers = [source, ]

    def register(self, node_id: int = 0) -> None:
        """记录一个经手人
        :param node_id: 经手人的 node_id
        """
        self.handlers.append(node_id)

    def copy(self):
        new_message = RegisteredMessage(self.data)
        new_message.handlers = self.handlers.copy
        return new_message

    @property
    def source(self):
        return self.handlers[0]


class NormalMessage(RegisteredMessage):
    """普通消息
    比 RegisteredMessage 多了 uuid 和 is_reply 两个属性
    """
    uuid: str
    is_reply: bool

    def __init__(self, uuid: str = '', is_reply: bool = False, data: str = '', source: int = 0):
        """
        :param uuid: 消息组的唯一标识
        :param is_reply: 该消息是否是对一个先前消息的回应
        :param data: 消息内容
        :param source: 源头发送者
        """
        super(NormalMessage, self).__init__(data, source)
        self.uuid = str(UUID(uuid)) if uuid else str(uuid4())
        self.is_reply = is_reply

    def copy(self):
        new_message = NormalMessage(self.uuid, self.is_reply, self.data)
        new_message.handlers = self.handlers.copy()
        return new_message
