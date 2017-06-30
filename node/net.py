#coding: utf-8

from abc import *
from socket import *
from select import *
from ctypes import *
import struct

SELECT = 0
EPOLL  = 1
POLL   = 2

class Session:
    def __init__(self, sock, net):
        self.sock = sock
        self.wbuf = ""
        self.rbuf = ""
        self.net = net
        self.msg_id = 0
        self.msg_len = 0
        self.msg_data = ""
        
    def send(self, msg_id, data):
        data_len = len(data) + 8
        buf = create_string_buffer(8)
        struct.pack_into('!I', buf, 0, msg_id)
        struct.pack_into('!I', buf, 4, data_len)
        self.wbuf += (buf.raw + data)
        self.net.set_writable(self.sock)
        
        
    def force_close(self):
        self.net.close_session(self)
        
class MsgHandle:
    @abstractmethod
    def on_receive_msg(self, session):
        pass
        
    @abstractmethod
    def on_session_close(self, session):
        pass
        
class DefMsgHandle(MsgHandle):
    def on_receive_msg(self, session):
        print 'receive msg from '+session.sock.getpeername()
        
    def on_session_close(self, session):
        print 'session close ' + session.sock.getpeername()
        
        
class Net:
    def __init__(self):
        self.type = 0
        self.session_map = {}
        self.msg_handle = DefMsgHandle()

    def init(self, type, host, port, timeout):
        if type == SELECT:
            self.init_as_select(host, port, timeout)
        elif type == POLL:
            self.init_as_poll(host, port, timeout)
        elif type == EPOLL:
            self.init_as_epoll(host, port, timeout)
        else:
            print "net init with error type."
    
    def register_msg_handle(self, handle):
        self.msg_handle = handle
            
    def dispatch_msg(self, session):
        self.msg_handle.on_receive_msg(session)
        
    def dispatch_close_msg(self, session):
        self.msg_handle.on_session_close(session)
        
    def set_writable(self, sock):
        if self.type == SELECT:
            if  sock not in self.write_list:
                self.write_list.append(sock)
        if self.type == EPOLL:
            self.epl.modify(sock.fileno(), EPOLLOUT)
        
    def update(self):
        if self.type == SELECT:
            self.update_as_select()
        elif self.type == EPOLL:
            self.update_as_epoll()
        elif self.type == POLL:
            self.update_as_poll()
        else:
            print "net update with error type."
            
    def recv(self, session, data):
        session.rbuf += data
        buf_data = session.rbuf
                    
        # 处理分包
        while len(buf_data) >= 8:
            session.msg_id = struct.unpack('!I', buf_data[0:4])[0]
            session.msg_len = struct.unpack('!I', buf_data[4:8])[0]
            # 判断包是否接收完整
            if len(buf_data) >= session.msg_len:
                session.msg_data = buf_data[8:session.msg_len]
                session.rbuf = buf_data[session.msg_len:]
                buf_data = session.rbuf
                        
                # 分发消息包给上层
                self.dispatch_msg(session)
                
            else:
                break  

                
    def connect_to(self, host, port):
        sock = socket(AF_INET, SOCK_STREAM, 0)
        sock.connect((host, port))
        sock.setblocking(False)
        if self.type == SELECT:
            self.read_list.append(sock)
            
        session = Session(sock, self)
        self.session_map[sock.fileno()] = session
        return session      
                
    def close_session(self, session):
        if self.type == SELECT:# SELECT模式
            if session.sock in self.read_list:
                self.read_list.remove(session.sock)
            if session.sock in self.write_list:
                self.write_list.remove(session.sock)
        elif self.type == EPOLL:# EPOLL模式
            self.epl.unregister(session.sock.fileno())
            
        # 从Session Map中移除
        del self.session_map[session.sock.fileno()]
                
        # close socket
        session.sock.close()     
        # 分发Session Close的消息给上层            
        self.dispatch_close_msg(session)
    
    # -----------------SELECT模式--------------------      
    def init_as_select(self, host, port, timeout):
        self.type = SELECT
        self.addr = (host, port)
        self.timeout = timeout
        
        self.srv_sock = socket(AF_INET, SOCK_STREAM, 0)
        self.srv_sock.setblocking(False)
        self.srv_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.srv_sock.bind(self.addr)
        self.srv_sock.listen(5)
        
        self.read_list = [self.srv_sock]
        self.write_list = []    


    def update_as_select(self):
        rs, ws, es = select(self.read_list, self.write_list, self.read_list, self.timeout)
        if not (rs or ws or es):
            print "timeout..."
            return
            
        # read
        for sock in rs:
            if sock is self.srv_sock:
                conn, addr = sock.accept()
                conn.setblocking(False)
                self.read_list.append(conn)
                self.session_map[conn.fileno()] = Session(conn, self)
            else:
                session = self.session_map[sock.fileno()]
                try:
                    data = sock.recv(1024)                
                    if data:
                        # 分包并分发消息
                        self.recv(session, data)
                    else:
                        self.close_session(session)
                except Exception,e:
                    print e
                    self.close_session(session)

        # write
        for sock in ws:
            session = self.session_map[sock.fileno()]
            if len(session.wbuf) > 0:
                sock.send(session.wbuf)
                session.wbuf = ""
                self.write_list.remove(sock)
                
        # except
        for sock in es:
            self.close_session(self.session_map[sock.fileno()])
            
            
    #-----------------EPOLL模式---------------------
    def init_as_epoll(self, host, port, timeout):
        self.type = EPOLL
        self.addr = (host, port)
        self.timeout = timeout
        
        self.srv_sock = socket(AF_INET, SOCK_STREAM, 0)
        self.srv_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.srv_sock.bind(self.addr)
        self.srv_sock.listen(5)
        self.srv_sock.setblocking(False)
        self.epl = epoll()
        self.epl.register(self.srv_sock.fileno(), EPOLLIN)
        
    def update_as_epoll(self):
        try:
            events = self.epl.poll(self.timeout)
            if not events:
                print "timeout..."
                return
        except:           
            return
            
        for fd, event in events:
            if fd == self.srv_sock.fileno():
                conn, addr = self.srv_sock.accept()                
                conn.setblocking(False)
                self.epl.register(conn.fileno(), EPOLLIN)
                session = Session(conn, self)
                self.session_map[conn.fileno()] = session
            else:
                session = self.session_map[fd]
                if event & EPOLLUP:
                    self.close_session(session)
                elif event & EPOLLIN:
                    data = session.sock.recv(1024)
                    if data:
                        self.recv(session, data)
                    else:
                        self.close_session(session)
                elif event & EPOLLOUT:
                    if len(session.wbuf) > 0:
                        session.sock.send(session.wbuf)
                        session.wbuf = ""
                    self.epl.modify(session.sock.fileno(), EPOLLIN)
        
    #-----------------POLL模式-----------------------
    def init_as_poll(self, host, port, timeout):
        print "Not implement."
        
    def update_as_poll(self):
        print "Not implement."
                    
                    
if __name__ == "__main__":
    net = Net()
    net.init(SELECT, "127.0.0.1", 8000, 0.01)
    while True:
        net.update()
        