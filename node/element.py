#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2017-07-04 13:38:24
# @Author  : kongyt (839339849@qq.com)
# @Link    : https://www.kongyt.com
# @Version : 1

from abc import *

Element_Msg_Id = 0x00000000

class Interface:
	@abstractmethod
	def send_element_msg(self, msg):
		print 'send element msg.'

class Element:
	def __init__(self, interface):
		self.guid = 0
		self.interface = interface

	@abstractmethod
	def on_message(self, msg):
		print 'msgId:', msg.msgId
		print 'from :', msg.eleFrom
		print 'to   :', msg.eleTo
		print 'data :', msg.data