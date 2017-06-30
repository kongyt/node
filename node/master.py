#coding: utf-8

import uuid

from net import *
from pb.mn_msg_pb2 import *


class NodeEntity:

    def __init__(self, session):
        self.session = session
        self.addr = None
        self.node_id = 0
        self.host = ""
        self.port = 0

    
    def get_node_id(self):
        return self.node_id
        
    def get_host(self):
        return self.host
        
    def get_port(self):
        return self.port
        

class Master(MsgHandle):

    def __init__(self):
        # 消息绑定
        self.msg_funcs = {
            N2M_Node_Connect_Req                : Master.onNodeConnectReq,              # Node 节点连接
            N2M_Get_Node_Id_Req                 : Master.onGetNodeIdReq,                # 获取Node Id
            N2M_Get_Node_List_Req               : Master.onGetNodeListReq,              # 获取Node 列表
            
            N2M_Register_Static_Element_Req    : Master.onRegisterStaticElementReq,   # 注册静态元素，为稳定服务指定一个固定的周知的UUID
            N2M_Register_Dynamic_Element_Req   : Master.onRegisterDynamicElementReq,  # 注册动态元素，生成一个UUID
            N2M_Unregister_Element_Req         : Master.onUnregisterElementReq,       # 取消注册元素，移除UUID
            N2M_Query_Element_Req              : Master.onQueryElementReq,            # 查询元素，查询一个UUID所指向的Node
        }
        
        # 所有session到NodeEntity的映射
        self.node_entity_map_by_session = {}
        # 所有node id 到NodeEntity的映射
        self.node_entity_map_by_id = {}
        self.element_map = {}
        self.max_node_id = 1
        
        
    def init_master(self, config):
        self.net = Net()
        self.net.register_msg_handle(self)
        self.net.init(SELECT, config['host'], config['port'], config['timeout'])
        while True:
            self.net.update()
            print 'node: '+str(len(self.node_entity_map_by_id))
            
        
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
        
    def onNodeConnectReq(self, session):
        print 'onNodeConnectReq'
        node = NodeEntity(session)
        self.node_entity_map_by_session[session] = node
        req = N2M_Request()
        req.ParseFromString(session.msg_data)
        if req.nodeConnectReq.hasNodeId is True:
            node.node_id = req.nodeConnectReq.nodeId
            self.node_entity_map_by_id[node.node_id] = node
            
        node.host = req.nodeConnectReq.host
        node.port = req.nodeConnectReq.port
        
        res = M2N_Response()
        res.result = True
        session.send(M2N_Node_Connect_Res, res.SerializeToString())
         
        
    def onGetNodeIdReq(self, session):
        print 'onGetNodeIdReq'
        if session in self.node_entity_map_by_session.keys():
            node = self.node_entity_map_by_session[session]
            res = M2N_Response()
            if node.node_id in self.node_entity_map_by_id.keys():
                res.result = False
                res.errorStr = 'Already get node id.'
                res.getNodeIdRes.nodeId = node.node_id
            else:
                node.node_id = self.max_node_id
                self.node_entity_map_by_id[node.node_id] = node
                self.max_node_id += 1
                res.result = True
                res.getNodeIdRes.nodeId = node.node_id
            session.send(M2N_Get_Node_Id_Res, res.SerializeToString())   
        else:
            session.force_close() # 异常状态，需要先发送NodeConnectReq
        
        
    def onGetNodeListReq(self, session):
        print 'onGetNodeListReq'
        if session in self.node_entity_map_by_session.keys():
            res = M2N_Response()
            res.result = True
            node = self.node_entity_map_by_session[session]
            for node_entity in self.node_entity_map_by_id.values():
                if node_entity != node:
                    node_info = res.getNodeListRes.nodes.add()
                    node_info.nodeId = node_entity.node_id
                    node_info.host = node_entity.get_host()
                    node_info.port = node_entity.get_port()
            session.send(M2N_Get_Node_List_Res, res.SerializeToString())                    
        else:
            session.force_close() # 异常状态，需要先发送NodeConnectReq
       
    def onRegisterStaticElementReq(self, session):
        print 'onRegisterStaticElementReq'
        if session in self.node_entity_map_by_session.keys():
            req = N2M_Request()
            req.ParseFromString(session.msg_data)
            
            res = M2N_Response()
            uuid_str = req.registerStaticElementReq.uuid
            if uuid_str not in self.element_map.keys():
                node = self.node_entity_map_by_session[session]
                if node.node_id == req.registerStaticElementReq.nodeId:
                    self.element_map[uuid_str] = node.node_id
                    res.result = True
                else:
                    res.result = False
                    res.errorStr = 'Node id incorrect.'
            else:
                res.result = False
                res.errorStr = 'Element UUID already exists.'
            session.send(M2N_Register_Static_Element_Res, res.SerializeToString())
        else:
            session.force_close() # 异常状态
            
        
    def onRegisterDynamicElementReq(self, session):
        print 'onRegisterDynamicElementReq'
        if session in self.node_entity_map_by_session.keys():
            req = N2M_Request()
            req.ParseFromString(session.msg_data)
            print req
            res = M2N_Response()
            uuid_str = str(uuid.uuid1()) # 生成UUID
            if uuid_str not in self.element_map.keys():
                node = self.node_entity_map_by_session[session]
                if node.node_id == req.registerDynamicElementReq.nodeId:
                    self.element_map[uuid_str] = node.node_id
                    res.result = True
                    res.registerDynamicElementRes.uuid = uuid_str
                else:
                    res.result = False
                    res.errorStr = 'Node id incorrect.'
            else:
                res.result = False
                res.errorStr = 'Element UUID already exists.'
            session.send(M2N_Register_Dynamic_Element_Res, res.SerializeToString())
        else:
            print 'force_close'
            session.force_close() # 异常状态
        
    def onUnregisterElementReq(self, session):
        print 'onUnregisterElementReq'
        if session in self.node_entity_map_by_session.keys():
            req = N2M_Request()
            req.ParseFromString(session.msg_data)
            
            res = M2N_Response()
            uuid_str = req.unregisterElementReq.uuid
            if uuid_str not in self.element_map.keys():
                node = self.node_entity_map_by_session[session]
                if node.node_id == self.element_map[uuid_str]:
                    del self.element_map[uuid_str]
                    res.result = True
                else:
                    res.result = False
                    res.errorStr = 'You do not own the element.'
            else:
                res.result = False
                res.errorStr = 'Element UUID do not exists.'
            session.send(M2N_Unregister_Element_Res, res.SerializeToString())
        else:
            session.force_close() # 异常状态
        
    def onQueryElementReq(self, session):
        print 'onQueryElementReq'
        req = N2M_Request()
        req.ParseFromString(session.msg_data)
        uuid_str = req.queryElementReq.uuid
        print self.element_map
        print uuid_str
        res = M2N_Response()
        if uuid_str not in self.element_map.keys():
            res.result = False
            res.errorStr = 'Cannot find element.'
        else:
            res.result = True
            res.queryElementRes.uuid = req.queryElementReq.uuid
            res.queryElementRes.nodeId = self.element_map[uuid_str]
        print res
        session.send(M2N_Query_Element_Res, res.SerializeToString())

        
if __name__ == "__main__":
    config = {}
    config["host"] = '127.0.0.1'
    config['port'] = 8000
    config['timeout'] = 10
    master = Master()
    master.init_master(config)
    