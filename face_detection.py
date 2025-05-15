import cv2
import face_recognition
import numpy as np
import os
import pickle
from datetime import datetime
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FaceDetector:
    """人脸检测与识别类"""

    def __init__(self, model_type='hog', tolerance=0.6, known_faces=None):
        """
        初始化人脸检测器

        参数:
            model_type (str): 使用的模型类型，'hog'（CPU）或'cnn'（GPU）
            tolerance (float): 人脸匹配的容差值，越小越严格
            known_faces (list): 已知人脸编码和对应用户信息的列表
        """
        self.model_type = model_type
        self.tolerance = tolerance
        self.known_faces = known_faces or []
        logger.info(f"人脸检测器初始化完成，使用{model_type}模型，容差值为{tolerance}")

    def load_known_faces(self, known_faces):
        """
        加载已知人脸数据

        参数:
            known_faces (list): 包含人脸编码和用户信息的列表
        """
        self.known_faces = known_faces
        logger.info(f"已加载{len(known_faces)}个已知人脸")

    def detect_faces(self, image):
        """
        检测图像中的人脸位置

        参数:
            image: 图像数据，可以是文件路径或图像数组

        返回:
            list: 人脸位置列表，每个位置为(top, right, bottom, left)
        """
        # 如果是文件路径，加载图像
        if isinstance(image, str):
            if not os.path.exists(image):
                logger.error(f"图像文件不存在: {image}")
                return []
            image = face_recognition.load_image_file(image)

        # 检测人脸位置
        start_time = time.time()
        face_locations = face_recognition.face_locations(image, model=self.model_type)
        detection_time = time.time() - start_time

        logger.info(f"检测到{len(face_locations)}个人脸，耗时{detection_time:.4f}秒")
        return face_locations

    def encode_faces(self, image, face_locations=None):
        """
        提取图像中人脸的编码特征

        参数:
            image: 图像数据，可以是文件路径或图像数组
            face_locations: 可选，人脸位置列表

        返回:
            list: 人脸编码特征列表
        """
        # 如果是文件路径，加载图像
        if isinstance(image, str):
            if not os.path.exists(image):
                logger.error(f"图像文件不存在: {image}")
                return []
            image = face_recognition.load_image_file(image)

        # 如果没有提供人脸位置，先检测人脸
        if face_locations is None:
            face_locations = self.detect_faces(image)

        if not face_locations:
            logger.warning("未检测到人脸，无法提取特征")
            return []

        # 提取人脸编码特征
        start_time = time.time()
        face_encodings = face_recognition.face_encodings(image, face_locations)
        encoding_time = time.time() - start_time

        logger.info(f"提取了{len(face_encodings)}个人脸特征，耗时{encoding_time:.4f}秒")
        return face_encodings

    def recognize_faces(self, face_encodings):
        """
        识别人脸，匹配已知人脸

        参数:
            face_encodings: 待识别的人脸编码特征列表

        返回:
            list: 识别结果列表，每个结果为(user_info, confidence)或(None, 0)
        """
        if not self.known_faces:
            logger.warning("没有已知人脸数据，无法进行识别")
            return [[] for _ in face_encodings]

        if not face_encodings:
            logger.warning("没有提供人脸特征，无法进行识别")
            return []

        results = []

        # 提取已知人脸的编码和用户信息
        known_encodings = [face['encoding'] for face in self.known_faces]

        for face_encoding in face_encodings:
            # 计算与已知人脸的距离
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)

            matched_users = []
            for i, distance in enumerate(face_distances):
                if distance <= self.tolerance:
                    confidence = 1 - distance
                    matched_users.append({
                        'user_info': {
                            'user_id': self.known_faces[i]['user_id'],
                            'student_id': self.known_faces[i]['student_id'],
                            'name': self.known_faces[i]['name']
                        },
                        'confidence': confidence
                    })

            results.append(matched_users)

        return results

    def process_image(self, image):
        """
        处理图像，检测、编码并识别人脸

        参数:
            image: 图像数据，可以是文件路径或图像数组

        返回:
            tuple: (face_locations, recognition_results)
        """
        # 检测人脸
        face_locations = self.detect_faces(image)

        if not face_locations:
            return [], []

        # 提取人脸编码
        face_encodings = self.encode_faces(image, face_locations)

        # 识别人脸
        recognition_results = self.recognize_faces(face_encodings)

        return face_locations, recognition_results

    def process_video_frame(self, frame):
        """
        处理视频帧，检测、编码并识别人脸

        参数:
            frame: 视频帧图像数组

        返回:
            tuple: (face_locations, recognition_results)
        """
        # 将BGR格式转换为RGB格式（OpenCV使用BGR，face_recognition使用RGB）
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 为提高性能，可以缩小图像
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)

        # 检测人脸
        face_locations = self.detect_faces(small_frame)

        # 调整人脸位置坐标到原始尺寸
        original_face_locations = []
        for top, right, bottom, left in face_locations:
            original_face_locations.append(
                (top * 4, right * 4, bottom * 4, left * 4)
            )

        if not original_face_locations:
            return [], []

        # 提取人脸编码（使用原始尺寸的图像）
        face_encodings = self.encode_faces(rgb_frame, original_face_locations)

        # 识别人脸
        recognition_results = self.recognize_faces(face_encodings)

        return original_face_locations, recognition_results

    def draw_results(self, image, face_locations, recognition_results):
        """
        在图像上绘制人脸检测和识别结果

        参数:
            image: 图像数组
            face_locations: 人脸位置列表
            recognition_results: 识别结果列表

        返回:
            image: 绘制结果后的图像
        """
        # 复制图像，避免修改原图
        result_image = image.copy()

        # 遍历每个人脸
        for i, (top, right, bottom, left) in enumerate(face_locations):
            if i < len(recognition_results):
                matched_users = recognition_results[i]

                # 绘制人脸框
                if matched_users:  # 识别成功
                    color = (0, 255, 0)  # 绿色
                else:  # 识别失败
                    color = (0, 0, 255)  # 红色

                cv2.rectangle(result_image, (left, top), (right, bottom), color, 2)

                # 绘制文本背景
                cv2.rectangle(result_image, (left, bottom - 35), (right, bottom), color, cv2.FILLED)

                # 绘制文��
                if matched_users:
                    text = f"{matched_users[0]['user_info']['name']} ({matched_users[0]['confidence']:.2f})"
                else:
                    text = f"Unknown"

                cv2.putText(result_image, text, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255),
                            1)

        return result_image

    @staticmethod
    def save_face_image(image, face_location, output_path):
        """
        保存人脸图像

        参数:
            image: 图像数组
            face_location: 人脸位置 (top, right, bottom, left)
            output_path: 输出文件路径

        返回:
            bool: 是否保存成功
        """
        try:
            top, right, bottom, left = face_location

            # 扩大人脸区域，包含更多背景
            height, width = image.shape[:2]
            margin = int((bottom - top) * 0.5)  # 使用人脸高度的50%作为边距

            # 确保不超出图像边界
            top = max(0, top - margin)
            bottom = min(height, bottom + margin)
            left = max(0, left - margin)
            right = min(width, right + margin)

            # 裁剪人脸区域
            face_image = image[top:bottom, left:right]

            # 保存图像
            cv2.imwrite(output_path, face_image)
            logger.info(f"人脸图像已保存到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"保存人脸图像失败: {e}")
            return False


def test_face_detector():
    """测试人脸检测器功能"""
    # 创建人脸检测器
    detector = FaceDetector()

    # 测试图像路径
    test_image_path = "test_image.jpg"

    # 检测人脸
    face_locations = detector.detect_faces(test_image_path)
    print(f"检测到 {len(face_locations)} 个人脸")

    # 提取人脸编码
    face_encodings = detector.encode_faces(test_image_path, face_locations)
    print(f"提取了 {len(face_encodings)} 个人脸特征")

    # 加载图像并绘制结果
    image = cv2.imread(test_image_path)
    result_image = detector.draw_results(image, face_locations, [(None, 0.5) for _ in face_locations])

    # 显示结果
    cv2.imshow("Face Detection Results", result_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test_face_detector()

