#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2017-07-03 19:52:48
# @Author  : kongyt (839339849@qq.com)
# @Link    : https://www.kongyt.com
# @Version : 1

import os
from net import *
from pb.mn_msg_pb2 import *

DISCONNECTED    = 0
CONNECTED       = 1
WORKING         = 2

class NodeInfo:
    def __init__(self, session):
        self.session = session
        self.node_id = 0
        self.host = ""
        self.port = 0
        self.stat = DISCONNECTED 
        self.guid_list = []

class Master(MsgHandle):
    def __init__(self):
        # 消息绑定
        self.msg_funcs = {
            N2M_Node_Connect_Req            : Master.on_node_connect_req,
            N2M_Node_Disconn_Req            : Master.on_node_disconn_req,
            N2M_Get_Node_List_Req           : Master.on_get_node_list_req,
            N2M_Register_Element_Req        : Master.on_register_element_req,
            N2M_Unregister_Element_Req      : Master.on_unregister_element_req,
            N2M_Query_Element_Req           : Master.on_query_element_req,
        }

        # 所有session到
        self.node_map = {}  # session -> node
        self.guid_map = {}  # guid    -> node

        self.max_node_id = 0
        self.max_guid = 100000

    def print_master_info(self):
        print ''
        print '-------------------------Master---------------------------'
        print 'node:', len(self.node_map)
        print 'element:', len(self.guid_map)
        print self.guid_map
        print ''

    def init_master(self, config):
        self.net = Net()
        self.net.register_msg_handle(self)
        self.net.init(SELECT, config['host'], config['port'], config['timeout'])
        while True:
            self.net.update()
            self.print_master_info()

    def on_receive_msg(self, session):
        if session.msg_id in self.msg_funcs.keys():
            self.msg_funcs[session.msg_id](self, session)
        else:
            print 'unkown msg type.('+str(session.msg_id)+')'

    def on_session_close(self, session):
        print 'Session close.'
        if session in self.node_map.keys():
            node = self.node_map[session]
            del self.node_map[session]
            if node.stat == WORKING:
                node.stat = DISCONNECTED
    
            for guid in node.guid_list:
                if guid in self.guid_map.keys():
                    del self.guid_map[guid]

    def on_node_connect_req(self, session):
        print 'Node connect.'
        res = M2N_Response()
        if session not in self.node_map.keys():
            node = NodeInfo(session)
            self.node_map[session] = node            
            req = N2M_Request()
            req.ParseFromString(session.msg_data)
            print req

            node.host = req.nodeConnectReq.host
            node.port = req.nodeConnectReq.port
            self.max_node_id += 1
            node.node_id = self.max_node_id

            node.stat = WORKING
            res.result = True
            res.nodeConnectRes.nodeId = node.node_id
        else:
            res.result = False
            res.errorStr = 'Node already connected.'
        session.send(M2N_Node_Connect_Res, res.SerializeToString())

    def on_node_disconn_req(self, session):
        print 'Node disconn.'
        res = M2N_Response()
        if session in self.node_map.keys():
            node = self.node_map[session]
            if node.stat == WORKING:
                node.stat = DISCONNECTED

            for guid in node.guid_list:
                if guid in self.guid_map.keys():
                    del self.guid_map[guid]
            del self.node_map[session]
            res.result = True
        else:
            res.result = False
            res.errorStr = 'Not connected.'
        session.send(M2N_Node_Disconn_Res, res.SerializeToString())


    def on_get_node_list_req(self, session):
        print 'Get node list.'
        res = M2N_Response()
        if session in self.node_map.keys():
            for sess in self.node_map.keys():
                if sess is not session:
                    node = self.node_map[sess]
                    node_info = res.getNodeListRes.nodeInfos.add()
                    node_info.nodeId = node.node_id
                    node_info.host = node.host
                    node_info.port = node.port
            res.result = True
        else:
            res.result = False
            res.errorStr = 'Not connected.'
        print res
        session.send(M2N_Get_Node_List_Res, res.SerializeToString())

    def on_register_element_req(self, session):
        print 'Register element.'
        res = M2N_Response()
        if session in self.node_map.keys():
            req = N2M_Request()
            req.ParseFromString(session.msg_data)

            node = self.node_map[session]
            if node.node_id == req.registerElementReq.nodeId:
                guid = 0
                if req.registerElementReq.isStatic is True:
                    guid = req.registerElementReq.guid
                else:
                    self.max_guid += 1
                    guid = self.max_guid
                if guid not in self.guid_map.keys():
                    self.guid_map[guid] = node
                    node.guid_list.append(guid)
                    res.result = True
                    res.registerElementRes.isStatic = req.registerElementReq.isStatic
                    res.registerElementRes.guid = guid
                else:
                    res.result = False
                    res.errorStr = 'GUID already exists.'
                    res.registerElementRes.guid = guid
            else:
                res.result = False
                res.errorStr = 'Node id error.'
        else:
            res.result = False
            res.errorStr = 'Not connected.'
        session.send(M2N_Register_Element_Res, res.SerializeToString())

    def on_unregister_element_req(self, session):
        print 'Unregister element.'
        res = M2N_Response()
        if session in self.node_map.keys():
            req = N2M_Request()
            req.ParseFromString(session.msg_data)
            guid = req.unregisterElementReq.guid
            if guid in self.guid_map.keys():
                node = self.guid_map[guid]
                node.guid_list.remove(guid)
                del self.guid_map[guid]
                res.result = True
            else:
                res.result = False
                res.errorStr = 'GUID not exists.'
        else:
            res.result = False
            res.errorStr = 'Not Connected.'
        session.send(M2N_Unregister_Element_Res, res.SerializeToString())

    def on_query_element_req(self, session):
        print 'Query element.'
        res = M2N_Response()
        if session in self.node_map.keys():
            req = N2M_Request()
            req.ParseFromString(session.msg_data)
            guid = req.queryElementReq.guid
            if guid in self.guid_map.keys():
                node = self.guid_map[guid]
                res.result = True
                res.queryElementRes.guid = guid
                res.queryElementRes.nodeId = node.node_id
            else:
                res.result = False
                res.errorStr = 'GUID not exists.'
                res.queryElementRes.guid = guid
        else:
            res.result = False
            res.errorStr = 'Not Connected.'
        session.send(M2N_Query_Element_Res, res.SerializeToString())


if __name__ == '__main__':
    config = {}
    config['host'] = '127.0.0.1'
    config['port'] = 8000
    config['timeout'] = 10
    master = Master()
    master.init_master(config) 