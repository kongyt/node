#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2017-07-05 14:15:55
# @Author  : kongyt (839339849@qq.com)
# @Link    : https://www.kongyt.com
# @Version : 1

import os
import sys
import struct
import time
from thread import start_new
from ctypes import *


from socket import *
from element import *
from pb.cn_msg_pb2 import *
from pb.element_msg_pb2 import *
from pb.chat_msg_pb2 import *

class ChatModule:
    def __init__(self, client):
        self.msg_handle = {}

    def register(self, msg_id, handle):
        self.msg_handle[msg_id] = handle


    def on_message(self, msg):
        if msg.msgId in self.msg_handle.keys():
            self.msg_handle[msg.msg_id](self, msg)

    def on_connect_chat_srv_res(self, msg):
        pass


class Client(Element, Interface):
    def __init__(self, host, port):
        Element.__init__(self, self)
        self.msg_id = 0
        self.msg_len = 0
        self.msg_data = ""
        self.rbuf = ""
        self.run_flag = True
        self.guid = 0
        self.sock = socket(AF_INET, SOCK_STREAM, 0)
        self.sock.connect((host, port))
        self.handle_map = {
            N2C_Client_Connect_Res    : Client.on_client_connect_res,
            N2C_Client_Disconn_Res    : Client.on_client_disconn_res,
            Element_Msg_Id              : Client.on_element_msg,
        }
        start_new(Client.recv_msg, (self, ))

    def send_client_connect_req(self, service, guid):
        req = C2N_Request()
        if service == True:
            req.clientConnectReq.isService = True
            req.clientConnectReq.guid = guid
        self.send_msg(C2N_Client_Connect_Req, req)

    def on_client_connect_res(self):
        res = N2C_Response()
        res.ParseFromString(self.msg_data)
        if res.result == True:
            print 'GUID:',res.clientConnectRes.guid
            self.guid = res.clientConnectRes.guid
        else:
            print 'connect error.'
            sys.exit(0)

    def send_client_disconn_req(self):
        req = C2N_Request()
        self.send_msg(C2N_Client_Disconn_Req, req)

    def on_client_disconn_res(self):
        self.run_flag = False
        self.sock.close()

    def run(self, service, guid):
        self.send_client_connect_req(service, guid)
        while self.run_flag:
            data = raw_input('>>>')
            if data:
                cmds = data.split()

                if cmds[0] == 'help':
                    self.help()
                elif cmds[0] == 'quit':
                    self.quit()
                elif cmds[0] == 'helo' and len(cmds) == 3:
                    self.helo(int(cmds[1]), cmds[2])
                elif len(cmds) == 4 and  cmds[0] == 'conn' and cmds[1] == 'chat' and cmds[2] == 'server':
                    self.chat_server_guid = int(cmds[3])
                    self.connect_chat_server(self.chat_server_guid)
                elif len(cmds) == 3 and  cmds[0] == 'disconn' and cmds[1] == 'chat' and cmds[2] == 'server':
                    self.disconn_chat_server(self.chat_server_guid)
                elif len(cmds) == 3 and cmds[0] == 'join' and cmds[1] == 'room':
                    self.room_id = int(cmds[2])
                    self.join_room(self.room_id)
                elif len(cmds) == 2 and cmds[0] == 'say':
                    self.say(cmds[1])
                elif len(cmds) == 3 and cmds[0] == 'leave' and cmds[1] == 'room':
                    self.leave_room(self.room_id)
                else :
                    print 'unkown command.'

    def connect_chat_server(self, guid):
        req = ChatReq()

        data = req.SerializeToString()

        msg = ElementMsg()
        msg.msgId = Connect_Chat_Srv_Req
        msg.eleFrom = self.guid
        msg.eleTo = guid
        msg.data = data
        self.send_element_msg(msg)
        

    def disconn_chat_server(self, guid):
        req = ChatReq()

        data = req.SerializeToString()

        msg = ElementMsg()
        msg.msgId = Disconn_Chat_Srv_Req
        msg.eleFrom = self.guid
        msg.eleTo = guid
        msg.data = data
        self.send_element_msg(msg)

    def join_room(self, room_id):
        req = ChatReq()
        req.joinRoomReq.roomId = room_id

        data = req.SerializeToString()

        msg = ElementMsg()
        msg.msgId = Join_Room_Req
        msg.eleFrom = self.guid
        msg.eleTo = self.chat_server_guid
        msg.data = data
        self.send_element_msg(msg)

    def say(self, txt):
        req = ChatReq()
        req.sayToRoomReq.roomId = self.room_id
        req.sayToRoomReq.txt = bytes(txt)

        data = req.SerializeToString()

        msg = ElementMsg()
        msg.msgId = Say_To_Room_Req
        msg.eleFrom = self.guid
        msg.eleTo = self.chat_server_guid
        msg.data = data
        print msg
        req = ChatReq()
        req.ParseFromString(data)
        self.send_element_msg(msg)

    def leave_room(self, room_id):
        req = ChatReq()
        req.leaveRoomReq.roomId = room_id

        data = req.SerializeToString()

        msg = ElementMsg()
        msg.msgId = Leave_Room_Req
        msg.eleFrom = self.guid
        msg.eleTo = self.chat_server_guid
        msg.data = data
        self.send_element_msg(msg)

    def helo(self, guid, txt):
        h = Helo()
        h.txt = txt
        data = h.SerializeToString()

        msg = ElementMsg()
        msg.msgId = Ele_Helo
        msg.eleFrom = self.guid
        msg.eleTo = guid
        msg.data = data
        self.send_element_msg(msg)

    def quit(self):
        self.send_client_disconn_req()

    def send_element_msg(self, msg):
        print 'send element msg.'
        self.send_msg(Element_Msg_Id, msg)

    def on_element_msg(self):
        msg = ElementMsg()
        msg.ParseFromString(self.msg_data)
        self.on_message(msg)

    def on_message(self, msg):
        print 'msgId:', msg.msgId
        print 'from :', msg.eleFrom
        print 'to   :', msg.eleTo
        if (msg.msgId & 0x00010000) == 0x00010000:
            m = None
            if msg.msgId != User_Say_Noti:
                m = ChatRes()
            else:
                m = ChatNoti()
            m.ParseFromString(msg.data)
            print 'data :', m
        else:
            print 'data :', msg.data


    def recv_msg(self):
        while self.run_flag == True:
            data = self.sock.recv(1024)
            if data:
                self.rbuf += data
                buf_data = self.rbuf
                while len(buf_data) >= 8:
                    self.msg_id = struct.unpack('!I', buf_data[0:4])[0]
                    self.msg_len = struct.unpack('!I', buf_data[4:8])[0]
                    if len(buf_data) >= self.msg_len:
                        self.msg_data = buf_data[8:self.msg_len]
                        self.rbuf = buf_data[self.msg_len:]
                        buf_data = self.rbuf
                        self.dispatch_msg()
                    else:
                        break
            else:
                self.run_flag = False
                print 'Server close session.'

    def dispatch_msg(self):
        print ''
        if self.msg_id in self.handle_map.keys():
            self.handle_map[self.msg_id](self)
        else:
            print 'unkown msg.'

    def send_msg(self, msg_id, msg):
        data = msg.SerializeToString()
        data_len = len(data) + 8
        buf = create_string_buffer(8)
        struct.pack_into('!I', buf, 0, msg_id)
        struct.pack_into('!I', buf, 4, data_len)
        wbuf = buf.raw + data
        self.sock.send(wbuf)


if __name__ == "__main__":
    print os.sys.argv 
    port = os.sys.argv[1]
    guid = None
    isService = False
    if len(os.sys.argv) == 3:
        guid = int(os.sys.argv[2])
        isService = True
    client = Client('127.0.0.1', int(port))
    client.run(isService, guid)