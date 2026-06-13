import socket
import struct
import argparse
import time
import threading
import pandas as pd
from datetime import datetime

LOG_FILE="run_log.txt"

WINDOW_SIZE=5   #发送窗口：5个包×80字节=400字节
PACKET_SIZE=80  #单包固定80字节
TOTAL_PACKETS=30    #总计发送30个数据包
TIMEOUT=0.3 #超时时间300ms

#GBN
base=1  #最早未确认的包
next_seqnum=1   #下一个要发送的包序号
lock=threading.Lock()   #线程锁保证多线程数据安全
send_times={}   #每个包最后一次发送时间
rtt_list=[] #存储所有RTT值
actual_send_count=0 #实际发送总包数
handshake_done=False    #握手完成标志
server_ip=""    #服务端ip
server_port=0   #服务端端口
time_start = 0.0  #计时器

def write_log(content):
    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    log_line=f"[{timestamp}][CLIENT]{content}\n"
    print(log_line.strip())
    with open(LOG_FILE,"a",encoding="utf-8") as f:
        f.write(log_line)

#根据包序号计算字节范围
def get_byte_range(seq):
    start_byte=(seq-1)*PACKET_SIZE+1
    end_byte=seq*PACKET_SIZE
    return start_byte,end_byte

#多线程，接收服务端ACK
def receive_acks(sock):
    global base,handshake_done,rtt_list,TIMEOUT, time_start
    while base<=TOTAL_PACKETS:
        try:
            packet,_=sock.recvfrom(1024)
            if len(packet)<13: continue
            _,msg_type,_,ack_num,data_len=struct.unpack(">HBIIH",packet[:13])

            #处理SYN-ACK，连接建立成功
            if msg_type==1:
                handshake_done=True
                write_log("收到服务端的确认！")
                handshake_ack = struct.pack(">HBIIH", 0, 6, 0, 0, 0)
                sock.sendto(handshake_ack, (server_ip, server_port))
                write_log("已发送第三次握手确认 ACK (Type=6)，正式完成三次握手！")

            #处理数据ACK，GBN累计确认
            elif msg_type==3:
                if ack_num==0:  # 握手相关的包或者特殊包，直接跳过计算RTT的逻辑
                    continue

                with lock:
                    if ack_num in send_times:
                        server_time = packet[13:13 + data_len].decode('ascii')  # 解析服务端返回的系统时间
                        s_byte, e_byte = get_byte_range(ack_num)

                        if ack_num>=base:
                            rtt_ms = (time.time() - send_times[ack_num]) * 1000
                            write_log(f"第{ack_num}个（第{s_byte}~{e_byte}字节）server端已经收到，RTT是{rtt_ms:.2f}ms(Server Time:{server_time})")

                            rtt_list.append(rtt_ms)
                            base = ack_num + 1  # 窗口滑动

                            #GBN收到合法ACK后重置计时器
                            if base < next_seqnum:
                                time_start = time.time()#窗口内还有未确认的包，重新开始倒计时

                            if rtt_list:
                                #更新超时时间
                                avg_rtt_ms=sum(rtt_list)/len(rtt_list)
                                raw_timeout=(avg_rtt_ms*5)/1000.0   #换算回秒
                                TIMEOUT = min(max(raw_timeout, 0.1), 1.0)  # 强制限制在 0.1秒 ~ 1.0秒 之间

                        else:write_log(f"第{ack_num}个（第{s_byte}~{e_byte}字节）收到重复确认(Duplicate ACK)")

        except socket.timeout:  #套接字超时
            continue

def main():
    global base,next_seqnum,actual_send_count,server_ip,server_port, time_start
    parser=argparse.ArgumentParser(description="UDP可靠传输客户端")
    parser.add_argument("ip",type=str,help="服务器IP")
    parser.add_argument("port",type=int,help="服务端端口")
    args=parser.parse_args()
    server_ip=args.ip
    server_port=args.port
    with open(LOG_FILE,"w",encoding="utf-8") as f:
        f.write("UDP客户端运行日志\n")

    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.settimeout(0.01)   #防止recvfrom永久阻塞线程

    #TCP模拟连接建立，SYN握手
    my_student_id=2118
    stu_id=my_student_id^0x5A3C
    write_log(f"发起握手请求（原始学号{my_student_id}，异或加密后：{stu_id}）")
    #封装SYN报文,Type=0
    syn_packet=struct.pack(">HBIIH",stu_id,0,0,0,0)
    sock.sendto(syn_packet,(server_ip,server_port))
    #启动后台收包线程
    recv_thread=threading.Thread(target=receive_acks,args=(sock,))
    recv_thread.daemon=True
    recv_thread.start()
    #等待握手成功，超时2秒退出
    timeout_start=time.time()
    while not handshake_done:
        if time.time()-timeout_start>2.0:
            write_log("握手超时，服务端无响应，程序退出。")
            return
        time.sleep(0.1)

    #GBN可靠数据传输
    write_log(f"开始GBN数据传输（窗口最大{WINDOW_SIZE*PACKET_SIZE}字节，共{TOTAL_PACKETS}个包）")
    time_start=time.time()
    while base<=TOTAL_PACKETS:
        with lock:
            while next_seqnum<base+WINDOW_SIZE and next_seqnum<=TOTAL_PACKETS:
                data_payload=b'X'*  PACKET_SIZE   #构造80字节数据载荷
                #封装DATA报文
                header=struct.pack(">HBIIH",0,2,next_seqnum,0,PACKET_SIZE)
                sock.sendto(header+data_payload,(server_ip,server_port))
                s_byte,e_byte=get_byte_range(next_seqnum)
                write_log(f"第{next_seqnum}个（第{s_byte}~{e_byte}字节）client端已经发送")
                if next_seqnum not in send_times:
                    send_times[next_seqnum]=time.time() #发送时间
                actual_send_count+=1    #实际发送次数
                if next_seqnum==base:
                    time_start=time.time()  #窗口左沿包发送：启动超时计时器
                next_seqnum+=1
            #超时检测
            if time.time()-time_start>TIMEOUT:
                write_log(f"【触发超时】{TIMEOUT*1000}ms内未收到确认，发生丢包")
                #重传
                for i in range(base,next_seqnum):
                    header=struct.pack(">HBIIH",0,2,i,0,PACKET_SIZE)
                    sock.sendto(header+(b'X'*PACKET_SIZE),(server_ip,server_port))
                    actual_send_count+=1
                    s_byte,e_byte=get_byte_range(i)
                    write_log(f"重传第{i}个（第{s_byte}~{e_byte}字节）数据包")
                    send_times[i] = time.time()
                time_start=time.time()  #重置计时器
        time.sleep(0.01)    #降低CPU占用

    #断开连接，FIN报文
    write_log("所有数据包均已被确认，发送FIN结束连接。")
    fin_packet=struct.pack(">HBIIH",0,4,0,0,0)
    sock.sendto(fin_packet,(server_ip,server_port))
    time.sleep(0.5)
    sock.close()

    #pandas统计
    df=pd.Series(rtt_list)  #把列表转换成一维序列
    task_loss_rate=(TOTAL_PACKETS/actual_send_count)*100
    real_loss_rate=((actual_send_count-TOTAL_PACKETS)/actual_send_count)*100
    # (实际发送总包数 - 成功送达总包数) / 实际发送总包数 × 100%
    print("【UDP可靠传输实验统计汇总】")
    print(f"目标发送包数：{TOTAL_PACKETS}，实际网卡发包总数：{actual_send_count}")
    print(f"丢包率：{task_loss_rate:.2f}%")
    print(f"真实丢包率：{real_loss_rate:.2f}%")
    print(f"最大RTT:{df.max():.2f}ms")
    print(f"最小RTT：{df.min():.2f}ms")
    print(f"平均RTT：{df.mean():.2f}ms")
    print(f"RTT标准差{df.std():.2f}ms")

if __name__=="__main__":
    main()