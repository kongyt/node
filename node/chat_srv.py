#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2017-07-05 16:01:52
# @Author  : kongyt (839339849@qq.com)
# @Link    : https://www.kongyt.com
# @Version : 1

import os


from service import *
from pb.chat_msg_pb2 import *


class ChatRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.users = [] #guid list

    def add_user(self, guid):
        if guid not in self.users:
            self.users.append(guid)
            return True
        else:
            return False

    def del_user(self, guid):
        if guid in self.users:
            self.users.remove(guid)

class ChatSrv(SrvBase):


    def init_chat_srv(self):
        self.chat_room = {}
        self.users = []
        self.element_msg_handle = {}
        self.register(Connect_Chat_Srv_Req, ChatSrv.on_connect_chat_srv_req)
        self.register(Disconn_Chat_Srv_Req, ChatSrv.on_disconn_chat_srv_req)
        self.register(Join_Room_Req,        ChatSrv.on_join_room_req)
        self.register(Say_To_Room_Req,      ChatSrv.on_say_to_room_req)
        self.register(Leave_Room_Req,       ChatSrv.on_leave_room_req)

    def register(self, msg_id, handle):
        self.element_msg_handle[msg_id] = handle

    def on_connect_chat_srv_req(self, msg):
        self.users.append(msg.eleFrom)
        res = ChatRes()
        res.result = True
        self.send_data_to_guid(msg.eleFrom, Connect_Chat_Srv_Res, res)

    def on_disconn_chat_srv_req(self, msg):
        self.users.remove(msg.eleTo)
        res = ChatRes()
        res.result = True
        self.send_data_to_guid(msg.eleFrom, Disconn_Chat_Srv_Res, res)

    def on_join_room_req(self, msg):
        req = ChatReq()
        req.ParseFromString(msg.data)
        room_id = req.joinRoomReq.roomId
        room = None 
        if room_id not in self.chat_room.keys():
            room = ChatRoom(room_id)
            self.chat_room[room_id] = room
        else:
            room = self.chat_room[room_id]
        room.add_user(msg.eleFrom)
        res = ChatRes()
        res.result = True
        res.joinRoomRes.roomId = room.room_id
        self.send_data_to_guid(msg.eleFrom, Join_Room_Res, res)

    def on_say_to_room_req(self, msg):
        req = ChatReq()
        req.ParseFromString(bytes(msg.data))
        room_id = req.sayToRoomReq.roomId 
        txt = req.sayToRoomReq.txt
        res = ChatRes()
        if room_id in self.chat_room.keys():
            room = self.chat_room[room_id]
            room_users = room.users
            noti = ChatNoti()
            noti.userSayNoti.user = msg.eleFrom
            noti.userSayNoti.txt = txt
            for user in room_users:
                if user != msg.eleFrom:
                    self.send_data_to_guid(user, User_Say_Noti, noti)
            res.result = True
        else:
            res.result = False
            res.errorStr = 'room not exists.'
        self.send_data_to_guid(msg.eleFrom, Say_To_Room_Res, res)

    def on_leave_room_req(self, msg):
        req = ChatReq()
        req.ParseFromString(msg.data)
        room_id = req.leaveRoomReq.roomId 
        res = ChatRes()
        if room_id in self.chat_room.keys():
            room = self.chat_room[room_id]
            room.del_user(msg.eleFrom)
            res.result = True
        else:
            res.result = False
            res.errorStr = 'room not exists.'
        self.send_data_to_guid(msg.eleFrom, Leave_Room_Res, res)

    def send_data_to_guid(self, guid, msg_id, packet):
        msg = ElementMsg()
        msg.eleFrom = self.guid
        msg.eleTo = guid
        data = packet.SerializeToString()
        msg.data = bytes(data)
        self.send_element_msg(msg)

    def on_message(self, msg):
        print msg
        if msg.msgId in self.element_msg_handle.keys():
            self.element_msg_handle[msg.msgId](self, msg)
        else:
            print 'unkown element msg.'



if __name__ == "__main__":
    print os.sys.argv 
    if len(os.sys.argv) == 3:
        port = os.sys.argv[1]
        guid = int(os.sys.argv[2])
        isService = True
        service = ChatSrv('127.0.0.1', int(port))
        service.init_chat_srv()
        service.run(guid)