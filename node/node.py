#coding: utf-8       
   
import os
import time   

from net import *
from pb.mn_msg_pb2 import *
from pb.nn_msg_pb2 import *
from pb.cn_msg_pb2 import *
from pb.element_msg_pb2 import *
from element import *


class TestElement(Element):
    def on_message(self, msg):
        print 'test element recv msg:' + msg.serializeData   

class ElementSession(Element):
        
    def set_session(self, session):
        self.session = session
    
    def on_message(self, msg):
        self.session.send(0x00000000, msg.SerializeToString())
        
class Node:
    def __init__(self):
        self.node_id = 0
        self.host = ""
        self.port = 0
        self.remote = False
        self.session = None
        self.is_working = False
        
    def connect(self, local_node_id, local_node_host, local_node_port):
        req = N2N_Request()
        req.nodeConnectReq.nodeId = local_node_id
        req.nodeConnectReq.host = local_node_host
        req.nodeConnectReq.port = local_node_port
        self.session.send(N2N_Node_Connect_Req, req.SerializeToString())
        
        
    def on_connect(self):
        self.is_working = True 
    
        
        

class NodeServer(MsgHandle, Interface):
    def __init__(self):
        # 消息绑定
        self.msg_funcs = {
            M2N_Node_Connect_Res    : NodeServer.onNodeConnectResFromMaster,
            M2N_Get_Node_Id_Res     : NodeServer.onGetNodeIdResFromMaster,
            M2N_Get_Node_List_Res   : NodeServer.onGetNodeListResFromMaster,
            M2N_Register_Static_Element_Res:    NodeServer.onRegisterStaticElementResFromMaster,
            M2N_Register_Dynamic_Element_Res:   NodeServer.onRegisterDynamicElementResFromMaster,
            M2N_Unregister_Element_Res:         NodeServer.onUnregisterElementResFromMaster,
            M2N_Query_Element_Res:              NodeServer.onQueryElementResFromMaster,
            
            N2N_Node_Connect_Req    : NodeServer.onNodeConnectReqFromNode,
            N2N_Node_Connect_Res    : NodeServer.onNodeConnectResFromNode,
            
            
            C2N_Client_Connect_Req  : NodeServer.onClientConnectReq,
            C2N_Client_Disconn_Req  : NodeServer.onClientDisconnReq,
            
            0x00000000              : NodeServer.onElementMsg,      # 0x00000000为元素消息ID
        }
        # 所有node id 到Node 的映射
        self.node_entity_map_by_session = {}
        self.node_entity_map_by_id = {}   
        self.local_node = None        
        self.master_session = None
        self.is_init_ok = False
        self.element_map = {}
        self.element_gateway = {}
        self.element_msg = []
        self.element_wait_register = []
        self.local_element = TestElement(self)
        self.element_map_by_session = {}
 

    def on_receive_msg(self, session):
        if session.msg_id in self.msg_funcs.keys():
            self.msg_funcs[session.msg_id](self, session)
        else:
            print 'unkown msg id.'
        
    def on_session_close(self, session):
        if session in self.node_entity_map_by_session.keys():
            node = self.node_entity_map_by_session[session]
            if node.node_id in self.node_entity_map_by_id.keys():
                del self.node_entity_map_by_id[node.node_id]
            del self.node_entity_map_by_session[session]
            
        
    def init(self, config):
        self.net = Net()
        self.net.register_msg_handle(self)
        self.net.init(SELECT, config['host'], config['port'], config['timeout'])
        self.local_node = Node()
        self.local_node.remote = False
        self.local_node.host = config['host']
        self.local_node.port = config['port']
        
        self.connect_to_master(config['master_host'], config['master_port'])
        
        self.run()
        
        
    def run(self):
        while True:
            self.net.update()
            for msg in self.element_msg:
                self.gate_element_msg_to_other_node(msg)            
                
            print 'node: '+str(len(self.node_entity_map_by_id)+1)     
    
        
    def connect_to_master(self, host, port):
        self.master_session = self.net.connect_to(host, port)
        req = N2M_Request()
        req.nodeConnectReq.hasNodeId = False
        req.nodeConnectReq.host = self.local_node.host
        req.nodeConnectReq.port = self.local_node.port
        self.master_session.send(N2M_Node_Connect_Req, req.SerializeToString())
    
    def get_node_id(self):
        req = N2M_Request()
        self.master_session.send(N2M_Get_Node_Id_Req, req.SerializeToString())
        
    def register_test_element(self):
        self.element_wait_register.append(self.local_element)
        req = N2M_Request()
        req.registerDynamicElementReq.nodeId = self.local_node.node_id
        print req
        self.master_session.send(N2M_Register_Dynamic_Element_Req, req.SerializeToString())
        
    def get_node_list(self):
        req = N2M_Request()
        self.master_session.send(N2M_Get_Node_List_Req, req.SerializeToString())
        
    def onNodeConnectResFromMaster(self, session):
        print 'onNodeConnectResFromMaster'
        res = M2N_Response()
        res.ParseFromString(session.msg_data)
        if res.result == True:
            self.get_node_id()
        else:
            print 'node connect master failed.'
        
    def onGetNodeIdResFromMaster(self, session):
        print 'onGetNodeIdResFromMaster'
        res = M2N_Response()
        res.ParseFromString(session.msg_data)
        if res.result == True:
            self.local_node.node_id = res.getNodeIdRes.nodeId
            self.local_node.is_working = True
            self.register_test_element()
            self.get_node_list()
        else:
            print 'get node id failed.'        
        
        
    def onGetNodeListResFromMaster(self, session):
        print 'onGetNodeListResFromMaster'
        res = M2N_Response()
        res.ParseFromString(session.msg_data)
        if res.result == True:
            for node_info in res.getNodeListRes.nodes:
                node = Node()
                node.remote = True
                node.node_id = node_info.nodeId
                node.host = node_info.host
                node.port = node_info.port
                node.session = self.net.connect_to(node.host, node.port)
                self.node_entity_map_by_session[node.session] = node
                node.connect(self.local_node.node_id, self.local_node.host, self.local_node.port) 
    
    def onRegisterStaticElementResFromMaster(self, session):
        print 'onRegisterStaticElementResFromMaster'
        
    def onRegisterDynamicElementResFromMaster(self, session):
        print 'onRegisterDynamicElementResFromMaster'
        res = M2N_Response()
        res.ParseFromString(session.msg_data)
        if res.result == True:
            element = self.element_wait_register.pop()
            element.uuid = res.registerDynamicElementRes.uuid
            print element.uuid
            self.element_map[element.uuid] = element
            self.element_gateway[element.uuid] = self.local_node.node_id
            print self.element_gateway
            if element is not self.local_element:
                res = N2C_Response()
                res.result = True
                res.clientConnectRes.uuid = element.uuid
                element.session.send(N2C_Client_Connect_Res, res.SerializeToString())
        else:
            print 'register dynamic element failed.'
            

    def unregister_element(self, uuid):
        req = N2M_Request()
        req.unregisterElementReq.nodeId = self.local_node.node_id
        req.unregisterElementReq.uuid = uuid
        self.master_session.send(N2M_Unregister_Element_Req, req.SerializeToString())
                
    
        
    def onUnregisterElementResFromMaster(self, session):
        print 'onUnregisterElementResFromMaster'        
        
    def onQueryElementResFromMaster(self, session):
        print 'onQueryElementResFromMaster'
        res = M2N_Response()
        res.ParseFromString(session.msg_data)
        if res.result == True:
            self.element_gateway[res.queryElementRes.uuid] = res.queryElementRes.nodeId
            print self.element_gateway
        else:
            print 'query element failed.'
    
        
    def onNodeConnectReqFromNode(self, session):
        print 'onNodeConnectReqFromNode'
        req = N2N_Request()
        req.ParseFromString(session.msg_data)
        node = Node()
        node.remote = True
        node.session = session
        node.host = req.nodeConnectReq.host
        node.port = req.nodeConnectReq.port
        node.node_id = req.nodeConnectReq.nodeId
        self.node_entity_map_by_session[session] = node
        self.node_entity_map_by_id[node.node_id] = node
        node.on_connect()
        res = N2N_Response()
        res.result = True
        session.send(N2N_Node_Connect_Res, res.SerializeToString())
        
        
        
    def onNodeConnectResFromNode(self, session):
        print 'onNodeConnectResFromNode'
        res = N2N_Response()
        res.ParseFromString(session.msg_data)
        if res.result == True:
            node = self.node_entity_map_by_session[session]
            self.node_entity_map_by_id[node.node_id] = node
            node.on_connect()    
            
    def onClientConnectReq(self, session):
        print 'onClientConnectReq'
        if not self.element_map_by_session.has_key(session):
            element = ElementSession(self)
            element.set_session(session)
            self.element_wait_register.append(element)        
            self.element_map_by_session[session] = element
            req = N2M_Request()
            req.registerDynamicElementReq.nodeId = self.local_node.node_id
            self.master_session.send(N2M_Register_Dynamic_Element_Req, req.SerializeToString())

    def onClientDisconnReq(self, session):
        print 'onClientDisconnReq'
        if self.element_map_by_session.has_key(session):
            element = self.element_map_by_session[session]
            self.unregister_element(element.uuid)
            del self.element_map[element.uuid]
            del self.element_map_by_session[session]
    
    
    def send_element_msg(self, msg):
        print 'node server send element msg'
        if self.element_gateway.has_key(msg.to_element):
            nodeid = self.element_gateway[msg.to_element]
            if nodeid == self.local_node.node_id:
                self.dispatch_element_msg(msg)
            else:
                node = self.node_entity_map_by_id[nodeid]
                node.session.send(0x00000000, msg.SerializeToString())
        else:
            self.element_msg.append(msg)
            
            req = N2M_Request()     
            req.queryElementReq.uuid = msg.to_element
            self.master_session.send(N2M_Query_Element_Req, req.SerializeToString())
    
    def gate_element_msg_to_other_node(self, msg):
        if self.element_gateway.has_key(msg.to_element):
            nodeid = self.element_gateway[msg.to_element]
            if self.node_entity_map_by_id.has_key(nodeid):
                node = self.node_entity_map_by_id[nodeid]
                node.session.send(0x00000000, msg.SerializeToString())
                self.element_msg.remove(msg)
                
    
    def dispatch_element_msg(self, msg):
        if self.element_map.has_key(msg.to_element):
            self.element_map[msg.to_element].on_message(msg)
        else:
            print 'no element'
            self.send_element_msg(msg)
           
    
    def onElementMsg(self, session):
        print 'onElementMsg'
        msg = ElementMsg()
        msg.ParseFromString(session.msg_data)
        self.dispatch_element_msg(msg)    
       
        

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
    node = NodeServer()
    node.init(config)
        