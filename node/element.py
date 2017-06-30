# coding: utf-8

from abc import *
from pb.element_msg_pb2 import *

class Interface:
    @abstractmethod
    def send_element_msg(self, msg):
        print 'send msg'

class Element:
    def __init__(self, interface):
        self.uuid = ""
        self.interface = interface

    @abstractmethod
    def on_message(self, msg):
        print msg.serializeData
        # self.interface.send(msg)
        