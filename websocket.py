import json
import socket
import threading

from flask import Flask, request, jsonify
from flask_cors import CORS

SERVER_IP = "0.0.0.0"
SERVER_PORT = 11111
FLASK_PORT = 22222
client_socket = None
connect_status = 0

temp_dict = {
    "0000": 17, "0001": 18, "0011": 19, "0010": 20,
    "0110": 21, "0111": 22, "0101": 23, "0100": 24,
    "1100": 25, "1101": 26, "1001": 27, "1000": 28,
    "1010": 29, "1011": 30
}

fan_speed_dict = {
    "101": "自动", "100": "低风", "010": "中风",
    "001": "高风", "000": "固定风"
}

mode_dict = {
    "10": "自动", "00": "制冷",
    "01": "送风", "11": "制热"
}

app = Flask(__name__)
CORS(app)


@app.route("/send", methods=["POST"])
def send_message():
    global client_socket
    if client_socket is None:
        return "", 503

    data = str(request.get_data().decode("utf-8"))
    if not data or len(data) != 16:
        return "", 400
    if data == "0111101111100000":
        status = {"IsOff": True}
    else:
        status = {"fan_speed": fan_speed_dict[f"{data[0]}{data[1]}{data[2]}"],
                  "temp": temp_dict[f"{data[8]}{data[9]}{data[10]}{data[11]}"],
                  "mode": mode_dict[f"{data[12]}{data[13]}"]}
    print("data:" + data)
    with open("./Remoter_Status.json", 'w+', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=4)
    client_socket.send(data.encode("ascii"))
    return "", 200


@app.route("/status", methods=["GET"])
def get_status():
    with open("./Remoter_Status.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        return jsonify(data), 200


@app.route("/connect_status")
def get_connect_status():
    global connect_status
    return str(connect_status), 200


def start_flask_server():
    app.run(host='127.0.0.1', port=FLASK_PORT, debug=False, use_reloader=False)


def start_tcp_server():
    global client_socket
    global connect_status
    # 创建 TCP 套接字
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_IP, SERVER_PORT))
    server_socket.listen(1)
    while True:
        try:
            # print("等待客户端连接...")
            connect_status = 0
            client_socket, client_address = server_socket.accept()
            print(f"客户端 {client_address} 已连接")
            client_socket.settimeout(30)
            connect_status = 1

            # 处理客户端连接
            while True:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break  # 客户端断开连接
                    if "HeartBeat" not in data.decode('utf-8'):
                        print(f"{data.decode('utf-8')}")
                except socket.timeout:
                    print("HeartBeat Timeout")
                    break
                except Exception as e:
                    print(f"接收数据失败: {e}")
                    break
        except Exception as e:
            print(f"TCP 服务器错误: {e}")
            connect_status = 0
        finally:
            if client_socket:
                client_socket.close()  # 关闭当前连接
            client_socket = None
            print("等待新的客户端连接...")


if __name__ == "__main__":
    tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
    tcp_thread.start()

    # 启动 Flask 服务
    start_flask_server()
