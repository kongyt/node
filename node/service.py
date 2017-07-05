#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2017-07-05 15:37:20
# @Author  : kongyt (839339849@qq.com)
# @Link    : https://www.kongyt.com
# @Version : 1

import os
import sys
import struct
import time
from ctypes import *


from socket import *
from element import *
from pb.cn_msg_pb2 import *
from pb.element_msg_pb2 import *

class SrvBase(Element, Interface):
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
            N2C_Client_Connect_Res      : SrvBase.on_client_connect_res,
            N2C_Client_Disconn_Res      : SrvBase.on_client_disconn_res,
            Element_Msg_Id              : SrvBase.on_element_msg,
        }

    def run(self, guid):
        self.send_client_connect_req(True, guid)
        self.recv_msg()


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
    if len(os.sys.argv) == 3:
        port = os.sys.argv[1]
        guid = int(os.sys.argv[2])
        isService = True
        service = SrvBase('127.0.0.1', int(port))
        service.run(guid)