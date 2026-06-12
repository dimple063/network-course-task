import socket
import struct
import threading
import argparse
from datetime import datetime

SERVER_HOST='0.0.0.0'   #允许任意IP的客户端连接

def write_log(content, client_addr=None):
    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    if client_addr:
        tag = f"[SERVER-ClientPort:{client_addr[1]}]"
    else:
        tag = f"[SERVER-MAIN]"
    print(f"[{timestamp}]{tag}{content}")

def handle_single_client(client_socket,client_addr):
    write_log(f"新客户端连接：{client_addr}", client_addr)
    try:
        #接收Initialization报文
        init_data=client_socket.recv(6)
        if not init_data:
            raise Exception("未收到初始化报文")
        msg_type,total_blocks=struct.unpack(">HI",init_data)    #>:大端序，H:2B无符号短整型，I:4B无符号整型
        write_log(f"收到Initialization报文(Type={msg_type}),总块数N={total_blocks}",client_addr)

        #发送agree报文
        agree_packet=struct.pack(">H",2)
        client_socket.sendall(agree_packet) #完整发送报文
        write_log(f"发送agree报文(Type=2)", client_addr)

        #循环处理每一块reverseRequst报文
        for block_id in range(1,total_blocks+1):
            rheader=client_socket.recv(6)   #读取报文头部
            if not rheader:break
            rtype,data_len=struct.unpack(">HI",rheader)
            rdata=b""
            while len(rdata)<data_len:
                packet=client_socket.recv(data_len-len(rdata))
                if not packet:break
                rdata+=packet
            rtext=rdata.decode("ascii") #解码为字符串
            write_log(f"收到reverseRequest报文(Type={rtype}),第{block_id}块，原始内容：{rtext}", client_addr)
            #文本反转
            reversed_text=rtext[::-1]
            reversed_data=reversed_text.encode("ascii") #重新编码为字节
            reversed_len=len(reversed_data)

            #发送reverseAnswer报文
            ans_packet=struct.pack(">HI",4,reversed_len) +reversed_data
            client_socket.sendall(ans_packet)
            write_log(f"发送reverseAnswer报文(Type=4),第{block_id}块，反转内容：{reversed_text}", client_addr)
    except Exception as e:
        write_log(f"客户端{client_addr}处理异常：{str(e)}", client_addr)
    finally:
        client_socket.close()
        write_log(f"客户端{client_addr}连接关闭\n", client_addr)

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="TCP文本反转服务端")
    parser.add_argument("port", type=int, nargs="?", default=8888, help="服务端监听端口")
    args = parser.parse_args()
    SERVER_PORT = args.port  # 从命令行动态获取端口，若未输入则默认为 8888

    server_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)  #创建一个基于IPv4的TCP服务端套接字
    server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1) #端口复用
    server_socket.bind((SERVER_HOST,SERVER_PORT)) #绑定IP和端口
    server_socket.listen(5)
    write_log(f"服务端启动成功，监听端口：{SERVER_PORT}")

    while True:
        client_conn,client_addr=server_socket.accept()  #客户端专属套接字，客户端地址
        client_thread=threading.Thread(target=handle_single_client,args=(client_conn,client_addr))#独立线程
        client_thread.daemon=True   #守护线程
        client_thread.start()