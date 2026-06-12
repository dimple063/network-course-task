import socket
import struct
import random
import argparse
from datetime import datetime

SERVER_IP='0.0.0.0' #服务端监听所有网卡地址
LOSS_RATE=0.3
LOG_FILE="run_log.txt"

def write_log(content):
    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    log_line=f"[{timestamp}][SERVER]{content}\n"
    print(log_line.strip())
    with open(LOG_FILE,'a',encoding='utf-8') as f:
        f.write(log_line)

def main():
    parser=argparse.ArgumentParser(description="UDP可靠传输服务端")
    parser.add_argument("port",type=int,nargs="?",default=8888,help="服务端监听端口")
    args=parser.parse_args()
    SERVER_PORT=args.port

    #创建UDP套接字
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.bind((SERVER_IP,SERVER_PORT))
    with open(LOG_FILE,"w",encoding="utf-8") as f:
        f.write("UDP服务端运行日志\n")

    write_log(f"UDP服务端启动成功，监听{SERVER_IP}:{SERVER_PORT}")
    write_log(f"当前设定的模拟丢包率为：{LOSS_RATE*100}%")

    expected_seq=1  #服务端期望接收的下一个数据包序号
    #持续监听客户端消息
    while True:
        try:
            packet,client_addr=sock.recvfrom(1024)
            if len(packet)<13:  continue
            student_id,msg_type,seq_num,ack_num,data_len=struct.unpack(">HBIIH",packet[:13])
            #协议格式：StudentID(2) + Type(1) + Seq(4) + Ack(4) + DataLen(2)
            #>HBIIH：大端序+2字节+1字节+4字节+4字节+2字节

            #处理连接建立请求
            if msg_type==0:  #SYN握手
                real_id=student_id^0x5A3C
                if 0<=real_id<=9999:
                    write_log(f"收到连接请求，学号验证通过（真实学号：{real_id}）")
                    ack_packet=struct.pack(">HBIIH",0,1,0,0,0)  #SYN-ACK(Type=1),确认连接建立
                    sock.sendto(ack_packet,client_addr)
                else:
                    write_log(f"错误：收到非法连接请求，解密学号为{real_id},拒绝连接！")

            #处理数据传输
            elif msg_type==2:
                rand_val=random.random()
                if rand_val<0.20:
                    write_log(f"【模拟丢包】随机丢弃了第{seq_num}个数据包，不予响应")
                    continue

                elif rand_val<0.30:
                    write_log(f"【模拟数据损坏】第{seq_num}个数据包校验失败，已丢弃，不予响应")
                    continue

                write_log(f"成功接收第{seq_num}个数据包，数据长度{data_len}字节")

                #GBN累计确认
                if seq_num==expected_seq:
                    expected_seq+=1

                server_time=datetime.now().strftime("%H-%M-%S").encode('ascii')
                #回复ACK报文(Type=3)，带累计确认号和服务器时间
                ack_header=struct.pack(">HBIIH",0,3,0,expected_seq-1,len(server_time))
                sock.sendto(ack_header+server_time,client_addr)
                write_log(f"发送累计确认ACK，确认已收到第{expected_seq-1}个数据包")

            #处理断开连接
            elif msg_type==4:
                write_log(f"收到客户端发来的结束报文，传输完成。重置状态等待下一次连接。\n"+"-"*40)
                fin_ack=struct.pack(">HBIIH",0,5,0,0,0)
                sock.sendto(fin_ack,client_addr)
                expected_seq=1  #重置序号，等待下一个客户端

            #处理客户端发送的第三次握手确认 ACK
            elif msg_type == 6:
                write_log(f"成功收到客户端 {client_addr} 的第三次握手确认 ACK (Type=6)！双端 TCP 模拟连接完全建立！")

        except Exception as e:
            write_log(f"发生异常：{e}")

if __name__=="__main__":
    main()

