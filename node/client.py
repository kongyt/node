#coding: utf-8

from socket import *
from pb.cn_msg_pb2 import *
from pb.element_msg_pb2 import *
from ctypes import *
import struct
from thread import start_new
import time

def recv_msg(client):
    while client.is_connected:
        data = client.sock.recv(1024)
        if data:
            client.rbuf += data
            buf_data = client.rbuf
            while len(buf_data) >= 8:
                client.msg_id = struct.unpack('!I', buf_data[0:4])[0]
                client.msg_len = struct.unpack('!I', buf_data[4:8])[0]
                if len(buf_data) >= client.msg_len:
                    client.msg_data = buf_data[8:client.msg_len]
                    client.rbuf = buf_data[client.msg_len:]
                    buf_data = client.rbuf
                    client.on_message()
                else:
                    break   
        else:
            client.is_connected = False
            client.server_close = True
            client.is_watting = False
            client.run_flag = False
            print 'Server Close session.'
    
    
class Client:
    def __init__(self):
        self.sock = socket(AF_INET, SOCK_STREAM, 0)
        self.is_connected = True
        self.rbuf = ""
        self.msg_id = 0
        self.msg_len = 0
        self.msg_data = ""
        self.run_flag = True
        self.is_waitting = False
        self.server_close = False
        self.handle_map = {
            N2C_Client_Connect_Res   : Client.on_connect_res,
            N2C_Client_Disconn_Res   : Client.on_disconn_res,
            0x00000000               : Client.on_element_msg,
        }
        
    def init_net(self, host, port):
        self.sock.connect((host, port))
        print 'connect success'
        start_new(recv_msg, (self,)) # 开一个线程用来接收数据
        self.send_conn()
        
    def run(self):        
        self.data_input()            # 输入线程主循环
        
        
    # 发送消息包
    def send_msg(self, msg_id, msg):
        self.is_waitting = True
        data = msg.SerializeToString()
        data_len = len(data) + 8
        buf = create_string_buffer(8)
        struct.pack_into('!I', buf, 0, msg_id)
        struct.pack_into('!I', buf, 4, data_len)
        wbuf = ""+buf.raw + data
        self.sock.send(wbuf)
    
    def on_message(self):
        if self.handle_map.has_key(self.msg_id):
            self.handle_map[self.msg_id](self)
        
        self.is_waitting = False    
        
    
    def data_input(self):
        while self.run_flag:           
            if self.is_waitting is True:
                time.sleep(0.02)
                continue
                
            data = raw_input(">>>")
            if data:
                cmds = data.split()
                
                flag = False
                # 非联网功能
                if cmds[0] == "help":
                    self.help()
                elif cmds[0] == "quit" or cmds[0] == 'q' or cmds[0] == 'Q':
                    self.quit()
                else:
                    flag = True
                if flag == False:
                    continue
            
                if self.server_close is True:
                    print "server quit."
                    continue
            
                # 需要联网的功能
                if cmds[0] == 'connect' and len(cmds) == 3:
                    self.init_net(cmds[1], int(cmds[2]))
                elif cmds[0] == 'helo' and len(cmds) == 3:
                    self.send_helo(cmds[1], cmds[2])
                else:
                    print "Unknown command."

                    
    def send_helo(self, to_uuid, txt):
        helo = Helo()
        helo.txt = txt
        data = helo.SerializeToString()
    
        msg = ElementMsg()
        msg.msgId = EM_HELO
        msg.from_element = self.uuid
        msg.to_element = to_uuid
        msg.serializeData = data
        self.send_msg(0x00000000, msg)
        self.is_waitting = False
        
    def help(self):
        print 'help'
        print 'connect <ip>   <port>'
        print 'helo    <uuid_to> <txt>'
        print 'quit'        
    
    def quit(self):
        self.send_disconn()
    
    def real_quit(self):
        self.run_flag = False
        self.is_connected = False
        self.sock.close()
        
    def send_conn(self):
        req = C2N_Request()
        self.send_msg(C2N_Client_Connect_Req, req)
        
    def send_disconn(self):
        req = C2N_Request()
        self.send_msg(C2N_Client_Disconn_Req, req)
        
    def on_connect_res(self):
        res = N2C_Response()
        res.ParseFromString(self.msg_data)
        if res.result == True:
            self.uuid = res.clientConnectRes.uuid
            print 'connect success.'
            print 'UUID:'+self.uuid
        else:
            print 'connect failed.'
    
    def on_disconn_res(self):
        self.real_quit()    
       
    def on_register_account(self):
        res = Response()
        res.ParseFromString(self.msg_data)
        if res.result == True:
            print "Register Success."
        else:
            self.stat = CONNECTED
            print "Register Failed: " + result.errorStr
    
    def on_element_msg(self):
        msg = ElementMsg()
        msg.ParseFromString(self.msg_data)
        print msg
            
            
if __name__ == "__main__":
    client = Client()
    client.run()
    print 'client quit.'
