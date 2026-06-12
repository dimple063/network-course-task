程序运行说明

 一、运行环境
1.服务端
	操作系统：Ubuntu 64位（VMware虚拟机）
	Python版本：Python 3.12.3
2.客户端
	操作系统：Windows 11
	Python版本：Python 3.9

二、文件列表
1.reversetcpclient.py : 客户端程序
2.reversetcpserver.py : 服务端程序
3.test.txt : 需要反转的英文ASCII文本文件
4.run_log.txt : 客户端运行日志（程序自动生成）
5.reverse_total.txt : 最终输出的反转文件（客户端生成）
6.tcp_packet_capture.doc：说明文档

三、配置选项
客户端运行时需指定5个命令行参数，格式：
python reversetcpclient.py [serverIP] [serverPort] [Lmin] [Lmax] [seed]

参数说明：
  serverIP：服务端IP地址（虚拟机IP：192.168.13.128）
  serverPort：服务端监听端口（默认8888）
  Lmin：文件分块最小长度（整数，>0）
  Lmax：文件分块最大长度（整数，≥Lmin）
  seed：随机分块种子

示例：
python reversetcpclient.py 192.168.13.128 8888 5 20 123

四、运行步骤
1. 启动服务端（Ubuntu虚拟机）
	打开终端，切换到代码目录，执行：
	python3 reversetcpserver.py
	服务端启动后会打印：「服务端启动成功，监听端口：8888（0.0.0.0）」，保持终端常开。

2. 启动客户端（Windows）
方式1：命令行运行
	打开CMD，切换到代码目录：
  	D:
  	cd OneDrive\桌面\241002118方沛锦\task1
	执行客户端命令：
  	python reversetcpclient.py 192.168.13.128 8888 5 20 123

方式2：PyCharm运行
	打开reversetcpclient.py，配置运行参数：192.168.13.128 8888 5 20 123
	点击运行按钮即可。