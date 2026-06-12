import socket
import struct
import random
import argparse
import os
import time
from datetime import datetime

INPUT_FILE="test.txt"
OUTPUT_FILE="reverse_total.txt"
LOG_FILE="run_log.txt"

def write_log(content):
    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    pid = os.getpid()  # 获取当前客户端的进程ID
    log_content = f"[{timestamp}][CLIENT-{pid}]{content}\n"
    print(log_content.strip())
    with open(LOG_FILE,"a",encoding="utf-8") as f:
        f.write(log_content)

def split_file_by_random_length(file_content,l_min,l_max,seed):
    random.seed(seed)
    chunks=[]
    current_pos=0
    total_length=len(file_content)

    if not isinstance(l_min, int) or not isinstance(l_max, int):
        raise ValueError("Lmin/Lmax必须为整数")
    if l_min>l_max or l_min<=0:
        raise ValueError(f"Lmin({l_min})必须>0且<=Lmax({l_max})")

    #循环分块
    while current_pos<total_length:
        remain_length=total_length-current_pos
        if remain_length<=l_min:
            chunk_length=remain_length
        elif remain_length<=l_max:
            chunk_length=remain_length
        else:
            chunk_length=random.randint(l_min,l_max)

        chunk=file_content[current_pos:current_pos+chunk_length]
        chunks.append(chunk)
        current_pos+=chunk_length
    return chunks,len(chunks)

if __name__=="__main__":
    #解析命令行参数
    parser=argparse.ArgumentParser(description="TCP文本反转客户端") #创建参数解析器
    parser.add_argument("server_ip",type=str,help="虚拟机服务端IP地址")
    parser.add_argument("server_port",type=int,nargs='?', default=8888,help="服务端端口（默认8888）")
    parser.add_argument("l_min",type=int,help="单块最小长度Lmin")
    parser.add_argument("l_max",type=int,help="单块最大长度Lmax")
    parser.add_argument("seed",type=int,help="随机分块种子")
    args=parser.parse_args() #解析命令行输入的参数

    with open(LOG_FILE,"a",encoding="utf-8") as f:
        f.write(f"\n--- TCP客户端启动 (进程PID: {os.getpid()}) ---\n")

    if not (1 <= args.server_port <= 65535):
        write_log(f"错误：端口{args.server_port}非法（必须1-65535）")
        exit(1)

    #读取本地文件
    try:
        with open(INPUT_FILE,"r",encoding="ascii") as f:
            file_content=f.read()
        write_log(f"读取文件{INPUT_FILE}完成，总长度：{len(file_content)}字节")
    except FileNotFoundError:
        write_log(f"错误：未找到文件{INPUT_FILE}，请先创建文件")
        exit(1)

    #计算总块数N
    chunks,total_blocks=split_file_by_random_length(file_content,args.l_min,args.l_max,args.seed)
    write_log(f"文件分块完成，总块数N={total_blocks}")

    #连接服务端
    client_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        client_socket.connect((args.server_ip,args.server_port))
        write_log(f"成功连接服务端{args.server_ip}:{args.server_port}")
    except ConnectionRefusedError:
        write_log("错误：无法连接服务端，请确认服务端已启动且IP/端口正确")
        exit(1)

    #发送Initialization报文
    init_packet=struct.pack(">HI",1,total_blocks)
    client_socket.sendall(init_packet)
    write_log(f"发送Initialization报文(Type=1)，总块数N={total_blocks}")

    #接收agree报文
    agree_data=client_socket.recv(2)
    agree_type=struct.unpack(">H",agree_data)[0]
    write_log(f"收到agree报文(Type={agree_type})")

    #循环发送reverseRequest，接收reverseAnswer
    all_reversed_content=[]
    for block_id,chunk in enumerate(chunks,1):
        chunk_bytes=chunk.encode("ascii")
        chunk_len=len(chunk_bytes)

        #发送reverseRequest报文
        rpacket=struct.pack(">HI",3,chunk_len)+chunk_bytes
        client_socket.sendall(rpacket)
        write_log(f"发送reverseRequest报文(Type=3)，第{block_id}块，长度{chunk_len}字节")

        #接收reverseAnswer报文
        ans_header=client_socket.recv(6)
        ans_type,reversed_len=struct.unpack(">HI",ans_header)
        reversed_data=b""
        while len(reversed_data)<reversed_len:
            packet=client_socket.recv(reversed_len-len(reversed_data))
            if not packet:break
            reversed_data+=packet
        reversed_text=reversed_data.decode("ascii")

        #终端打印
        print(f"{block_id}:{reversed_text}")
        all_reversed_content.append(reversed_text)
        write_log(f"收到reverseAnswer报文(Type={ans_type}),第{block_id}块，反转内容：{reversed_text}")
        time.sleep(0.01)

    all_reversed_content.reverse()  # 仅把列表里数据块的整体顺序倒置
    final_reversed_text = "".join(all_reversed_content)
    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(final_reversed_text)
    write_log(f"完整反转文件{OUTPUT_FILE}生成完成！")

    client_socket.close()
    write_log("客户端连接关闭，程序结束")