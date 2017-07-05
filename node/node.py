#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2017-07-04 13:36:05
# @Author  : kongyt (839339849@qq.com)
# @Link    : https://www.kongyt.com
# @Version : 1

import os
import sys
import time

from net import *
from pb.mn_msg_pb2 import *
from pb.nn_msg_pb2 import *
from pb.cn_msg_pb2 import *
from pb.element_msg_pb2 import *
from element import *


class ElementSession(Element):
    def __init__(self, session, interface):
        Element.__init__(self, interface)
        self.guid = 0
        self.session = session

    def on_message(self, msg):
        self.session.send(Element_Msg_Id, msg.SerializeToString())

class Node:
    def __init__(self):
        self.node_id = 0
        self.host = ''
        self.port = 0


class RemoteNode(Node):
    def __init__(self, session):
        Node.__init__(self)
        self.session = session
        self.guid_list = []

    def relay_element_msg(self, msg):
        self.session.send(Element_Msg_Id, msg.SerializeToString())


class LocalNode(Node, MsgHandle, Interface):
    def __init__(self, config):
        Node.__init__(self)
        # 消息绑定
        self.msg_funcs = {
            M2N_Node_Connect_Res        :    LocalNode.on_node_connect_res_from_master,
            M2N_Node_Disconn_Res        :    LocalNode.on_node_disconn_res_from_master,
            M2N_Get_Node_List_Res       :    LocalNode.on_get_node_list_res_from_master,
            M2N_Register_Element_Res    :    LocalNode.on_register_element_res_from_master,
            M2N_Unregister_Element_Res  :    LocalNode.on_unregister_element_res_from_master,
            M2N_Query_Element_Res       :    LocalNode.on_query_element_res_from_master,

            N2N_Node_Connect_Req        :    LocalNode.on_node_connect_req_from_node,
            N2N_Node_Connect_Res        :    LocalNode.on_node_connect_res_from_node,

            C2N_Client_Connect_Req      :    LocalNode.on_client_connect_req_from_client,
            C2N_Client_Disconn_Req      :    LocalNode.on_client_disconn_req_from_client,

            Element_Msg_Id              :    LocalNode.on_receive_element_msg,
        }

        self.remote_node_map = {}    # session -> node
        self.element_map = {}        # session -> element
        self.node_id_map = {}        # node_id -> node
        self.guid_to_node = {}       # guid      -> node
        self.guid_to_element = {}    # guid      -> element
        self.node_id = 0
        self.host = config['host']
        self.port = config['port']
        self.timeout =config['timeout']
        self.master_host = config['master_host']
        self.master_port = config['master_port']
        self.master_session = None

        self.wait_proc_msg = {}        # guid    -> msg


        self.service_element_wait_register = {}
        self.dynamic_element_wait_register = []

    def init_local_node(self):
        self.net = Net()
        self.net.register_msg_handle(self)
        self.net.init(SELECT, self.host, self.port, self.timeout)
        self.master_session = self.net.connect_to(self.master_host, self.master_port)    # 连接Master
        self.send_node_connect_req_to_master(self.host, self.port)        # 发送连接请求

        while True:
            self.net.update()
            for guid in self.wait_proc_msg.keys():
                if guid in self.guid_to_node.keys():
                    node = self.guid_to_node[guid]
                    for msg in self.wait_proc_msg[guid]:
                        node.relay_element_msg(msg)
                    self.wait_proc_msg[guid] = []
                    del self.wait_proc_msg[guid]
                    
            self.print_node_info()


    def print_node_info(self):
        print ''
        print '-------------------------Node---------------------------'
        print 'node id:', self.node_id
        print 'node:', len(self.remote_node_map)+1
        print 'element:', len(self.element_map)
        print self.node_id_map
        print ''


    def on_receive_msg(self, session):
        if session.msg_id in self.msg_funcs.keys():
            self.msg_funcs[session.msg_id](self, session)
        else:
            print 'unkown msg id.'

    def on_session_close(self, session):
        if session in self.remote_node_map.keys():
            remote_node = self.remote_node_map[session]
            for guid in remote_node.guid_list:
                if guid in self.guid_to_node.keys():
                    del self.guid_to_node[guid]
                if guid in self.wait_proc_msg.keys():
                    del self.wait_proc_msg[guid]
            if remote_node.node_id in self.node_id_map.keys():
                del self.node_id_map[remote_node.node_id]

        elif session in self.element_map.keys():
            element = self.element_map[session]            
            if element.guid in self.guid_to_element.keys():
                self.send_unregister_element_req_to_master(element.guid)
                del self.guid_to_element[element.guid]
            del self.element_map[session]
        else:
            print 'empty session close.'



    def on_receive_element_msg(self, session):
        msg = ElementMsg()
        msg.ParseFromString(session.msg_data)
        if msg.eleTo in self.guid_to_element.keys():            # 如果是自己管理的，则直接发送过去
            self.guid_to_element[msg.eleTo].on_message(msg)    
        elif msg.eleTo in self.guid_to_node.keys():            # 如果是其他节点管理的，并且知道路由信息，则转发
            self.guid_to_node[msg.eleTo].relay_element_msg(msg)
        else:    # 路径未知，加入待处理消息容器
            if msg.eleTo in self.wait_proc_msg.keys():
                self.wait_proc_msg[msg.eleTo].append(msg)
            else:
                self.wait_proc_msg[msg.eleTo] = []
                self.wait_proc_msg[msg.eleTo].append(msg)
            # 发送元素路由查询请求
            self.send_query_element_req(msg.eleTo)


    # 发送连接Master请求
    def send_node_connect_req_to_master(self, host, port):
        req = N2M_Request()
        req.nodeConnectReq.host = host
        req.nodeConnectReq.port = port
        self.master_session.send(N2M_Node_Connect_Req, req.SerializeToString())

    def on_node_connect_res_from_master(self, session):
        if session is self.master_session:
            res = M2N_Response()
            res.ParseFromString(session.msg_data)
            if res.result == True:
                self.node_id = res.nodeConnectRes.nodeId
                self.send_get_node_list_req()
            else:
                print 'Get node id error.'
                sys.exit(0)
        else:
            print 'session error.'
            session.force_close()

    # 发送断开Master连接请求
    def send_node_disconn_req_to_master(self):
        req = N2M_Request()
        self.master_session.send(N2M_Node_Disconn_Req, req.SerializeToString())

    def on_node_disconn_res_from_master(self, session):
        print 'disconn master.'
        session.force_close()

    def send_get_node_list_req(self):
        req = N2M_Request()
        self.master_session.send(N2M_Get_Node_List_Req, req.SerializeToString())

    def on_get_node_list_res_from_master(self, session):
        if session is self.master_session:
            res = M2N_Response()
            res.ParseFromString(session.msg_data)
            print res
            for node_info in res.getNodeListRes.nodeInfos:
                node_session = self.net.connect_to(node_info.host, node_info.port)
                node = RemoteNode(node_session)
                node.host = node_info.host
                node.port = node_info.port
                node.node_id = node_info.nodeId
                self.remote_node_map[node_session] = node
                self.node_id_map[node.node_id] = node
                self.send_node_connect_req_to_node(node_session, self.node_id, self.host, self.port)
        else:
            session.force_close()


    # 发送节点连接请求
    def send_node_connect_req_to_node(self, session, local_node_id, local_host, local_port):
        req = N2N_Request()
        req.nodeConnectReq.nodeId = local_node_id
        req.nodeConnectReq.host = local_host
        req.nodeConnectReq.port = local_port
        print req
        session.send(N2N_Node_Connect_Req, req.SerializeToString())

    # 响应节点连接请求
    def on_node_connect_req_from_node(self, session):
        res = N2N_Response()
        if session not in self.remote_node_map.keys():
            req = N2N_Request()
            req.ParseFromString(session.msg_data)
            node = RemoteNode(session)
            node.host = req.nodeConnectReq.host
            node.port = req.nodeConnectReq.port
            node.node_id = req.nodeConnectReq.nodeId
            self.remote_node_map[session] = node
            self.node_id_map[node.node_id] = node

            res.result = True
        else:
            res.result = False
            res.errorStr = 'Node already connected.'
        print res
        session.send(N2N_Node_Connect_Res, res.SerializeToString())

    # 响应节点连接回复
    def on_node_connect_res_from_node(self, session):
        print 'node connect success'


    def send_register_element_req_to_master(self, element, isStatic, guid):
        req = N2M_Request()
        req.registerElementReq.nodeId = self.node_id
        if isStatic == True:
            req.registerElementReq.isStatic = True
            req.registerElementReq.guid = guid
        else:
            req.registerElementReq.isStatic = False
        print req
        self.master_session.send(N2M_Register_Element_Req, req.SerializeToString())

    def on_register_element_res_from_master(self, session):
        if session is self.master_session:
            res = M2N_Response()
            res.ParseFromString(session.msg_data)
            print res
            guid = res.registerElementRes.guid 
            if res.registerElementRes.isStatic == True:                
                if guid not in self.guid_to_element.keys():
                    if guid in self.service_element_wait_register.keys():
                        element = self.service_element_wait_register[guid]
                        del self.service_element_wait_register[guid]
                        self.guid_to_element[guid] = element
                        res = N2C_Response()
                        res.result = True
                        res.clientConnectRes.guid = guid
                        element.session.send(N2C_Client_Connect_Res, res.SerializeToString())
                    else:
                        print 'no service element wait register.'
                else:
                    print 'guid already exist in element map.'
            else:
                if len(self.dynamic_element_wait_register) > 0:
                    element = self.dynamic_element_wait_register.pop()
                    element.guid = guid
                    if guid not in self.guid_to_element.keys():
                        self.guid_to_element[guid] = element
                        res = N2C_Response()
                        res.result = True
                        res.clientConnectRes.guid = guid
                        element.session.send(N2C_Client_Connect_Res, res.SerializeToString())
                    else:
                        print 'dynamic guid already exist in element map.'
                else:
                    print 'no dynamic element wait register.'
        else:
            session.force_close()

    # 发送取消注册元素请求
    def send_unregister_element_req_to_master(self, guid):
        req = N2M_Request()
        req.unregisterElementReq.guid = guid
        self.master_session.send(N2M_Unregister_Element_Req, req.SerializeToString())

    def on_unregister_element_res_from_master(self, session):
        if session is self.master_session:
            print 'unregister element success.'
        else:
            session.force_close()


    # 发送查询请求
    def send_query_element_req(self, guid):
        req = N2M_Request()
        req.queryElementReq.guid = guid
        self.master_session.send(N2M_Query_Element_Req, req.SerializeToString())

    # 响应查询请求
    def on_query_element_res_from_master(self, session):
        if session is self.master_session:
            res = M2N_Response()
            res.ParseFromString(session.msg_data)
            print res
            if res.result == True:
                guid = res.queryElementRes.guid
                node_id = res.queryElementRes.nodeId
                if guid not in self.guid_to_node.keys():
                    if node_id in self.node_id_map.keys():
                        self.guid_to_node[guid] = self.node_id_map[node_id]
                    else:
                        print 'not connected to node.'
                else:
                    print 'already has guid gate info.'
        else:
            session.force_close()

    def on_client_connect_req_from_client(self, session):        
        if session not in self.element_map.keys():
            element = ElementSession(session, self)
            self.element_map[session] = element
            req = C2N_Request()
            req.ParseFromString(session.msg_data)
            print req
            guid = 0
            isService = req.clientConnectReq.isService 
            if isService is True:
                guid = req.clientConnectReq.guid
                element.guid = guid
                self.service_element_wait_register[guid] = element
            else:
                self.dynamic_element_wait_register.append(element)            

            self.send_register_element_req_to_master(element, isService, guid)
        else:
            res = N2C_Response()
            res.result = False
            res.errorStr = 'already connected.'
            session.send(N2N_Node_Connect_Res, res.SerializeToString())

    def on_client_disconn_req_from_client(self, session):
        session.force_close()
        print 'client disconn.'


if __name__ == "__main__":
    config = {}
    config['host'] = '127.0.0.1'
    if len(os.sys.argv) == 2:
        config['port'] = int(os.sys.argv[1])
    else:
        config['port'] = 8001
    print config['port']
    config['timeout'] = 10
    config['master_host'] = '127.0.0.1'
    config['master_port'] = 8000
    node = LocalNode(config)
    node.init_local_node()


