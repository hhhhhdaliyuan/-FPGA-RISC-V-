import socket
import numpy as np
import cv2

# 配置网络与图像参数
UDP_IP = "192.168.1.105"  # 你的上位机电脑IP
UDP_PORT = 8080  # 监听的UDP端口 (0x1F90)
IMG_WIDTH = 1280  # 图像宽度
IMG_HEIGHT = 720  # 图像高度
PAYLOAD_SIZE = 1400  # 每包有效数据量

# 计算一帧所需的总字节数 (RGB565每个像素占2个字节)
BYTES_PER_FRAME = IMG_WIDTH * IMG_HEIGHT * 2


def main():
    # 建立 UDP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"Server listening on {UDP_IP}:{UDP_PORT}")
    print("Waiting for FPGA video stream...")

    frame_buffer = bytearray()
    current_frame_id = -1

    while True:
        # 接收数据，缓冲区设置稍大于1408即可
        data, addr = sock.recvfrom(2048)

        # 检查是否为自定义协议的数据包头：0xA5 0x5A
        if len(data) >= 8 and data[0] == 0xA5 and data[1] == 0x5A:
            # 提取报头信息
            frame_id = (data[2] << 8) | data[3]
            seq_num = (data[4] << 8) | data[5]
            payload_len = (data[6] << 8) | data[7]

            # 提取有效图像载荷
            payload = data[8: 8 + payload_len]

            # 判断是否为新的一帧
            if frame_id != current_frame_id:
                # 若上一帧图像还没满就被强制换帧，丢弃残留数据
                if len(frame_buffer) > 0 and len(frame_buffer) != BYTES_PER_FRAME:
                    print(f"Warning: Frame {current_frame_id} incomplete, dropping.")

                current_frame_id = frame_id
                frame_buffer = bytearray()  # 清空并开启新帧的缓存

            # 将当前包的图像数据存入帧缓存
            if len(frame_buffer) < BYTES_PER_FRAME:
                frame_buffer.extend(payload)

            # 当收集满了一整帧的字节数时，进行解码和显示
            if len(frame_buffer) == BYTES_PER_FRAME:
                # 将字节数组转换为 16-bit 整数 (RGB565)
                # 因为FPGA是先发高位(15:8)再发低位(7:0)，属于大端序(Big-Endian)
                img_uint16 = np.frombuffer(frame_buffer, dtype='>u2').reshape((IMG_HEIGHT, IMG_WIDTH))

                # 按照 RGB565 格式提取 R, G, B 通道，并映射到 8-bit (0-255)
                r = ((img_uint16 >> 11) & 0x1F).astype(np.float32) * (255.0 / 31.0)
                g = ((img_uint16 >> 5) & 0x3F).astype(np.float32) * (255.0 / 63.0)
                b = (img_uint16 & 0x1F).astype(np.float32) * (255.0 / 31.0)

                # 合并为 OpenCV 默认的 BGR 格式
                bgr_img = cv2.merge([b.astype(np.uint8), g.astype(np.uint8), r.astype(np.uint8)])

                # 显示图像
                cv2.imshow("FPGA Original Video Stream", bgr_img)

                # 必须加入 waitKey 保证 OpenCV 窗口能够刷新
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("Exiting...")
                    sock.close()
                    cv2.destroyAllWindows()
                    return


if __name__ == "__main__":
    main()