import cv2
from PIL import Image
import numpy as np
import time

# Initialize cameras
front_cam = cv2.VideoCapture(2)  # Front camera
bottom_cam = cv2.VideoCapture(0)  # Bottom camera

# Define fixed variables
lower_bound_orange, upper_bound_orange = np.array([6, 120, 60]), np.array([23, 255, 255])
lower_bound_red1, upper_bound_red1 = np.array([0, 100, 80]), np.array([2, 255, 255])
lower_bound_red2, upper_bound_red2 = np.array([165, 100, 80]), np.array([179, 255, 255])

#bottom_cam_target_x, bottom_cam_target_y = 0, 0
bottom_cam_target_x, bottom_cam_target_y = 320, 75
front_width, front_height, bottom_width, bottom_height = None, None, None, None

# Global variables
offset_x_front, offset_x_bottom, offset_y_bottom = None, None, None
object_detected, lift_object, bucket_detected = False, False, False

# FUNCTIONS
def detect_orange(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask_orange = cv2.inRange(hsv, lower_bound_orange, upper_bound_orange)
    contours_orange, _ = cv2.findContours(mask_orange, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours_orange

def detect_red(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask_red1 = cv2.inRange(hsv, lower_bound_red1, upper_bound_red1)
    mask_red2 = cv2.inRange(hsv, lower_bound_red2, upper_bound_red2)
    mask_red = cv2.bitwise_or(mask_red1, mask_red2)
    contours_red, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours_red

def draw_line_bottom(frame, target_point, object_point):
    cv2.line(frame, target_point, object_point, color=(0, 255, 0), thickness=3)
    return frame

def draw_polyline_front(frame, object_point):
    bottom_center = (front_width // 2, front_height)
    points = [
        bottom_center,
        ((bottom_center[0] + object_point[0]) // 2, front_height - 50),
        ((bottom_center[0] + object_point[0]) // 2, object_point[1] + 50),
        object_point
    ]
    points = np.array(points, np.int32)
    points = points.reshape((-1, 1, 2))
    cv2.polylines(frame, [points], isClosed=False, color=(0, 255, 0), thickness=3)
    return frame

def Bottom_Cam_Function(frame, contours):
    """
    Get the OBJECT CENTER's distance from the TARGET COORDINATE
    >> used in stage 1 to align
    >> used in stage 3 to align 
    """
    # TARGET COORDINATE
    cv2.circle(frame, (bottom_cam_target_x, bottom_cam_target_y), 7, (255, 0, 255), -1)
    cv2.putText(frame, f" Target point: ({bottom_cam_target_x}, {bottom_cam_target_y})", (bottom_cam_target_x - 70, bottom_cam_target_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # OBJECT CENTER
    largest_contour = max(contours, key=cv2.contourArea)
    M = cv2.moments(largest_contour)
    if M["m00"] >= 100:
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        cv2.drawContours(frame, [largest_contour], -1, (0, 255, 0), 2)
        cv2.circle(frame, (cX, cY), 7, (255, 0, 0), -1)
        cv2.putText(frame, f"Center: ({cX}, {cY})", (cX - 50, cY - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # CALCULATION
        draw_line_bottom(frame, (bottom_cam_target_x, bottom_cam_target_y), (cX, cY))
        offset_x, offset_y = cX - bottom_cam_target_x, cY - bottom_cam_target_y
        return frame, offset_x, offset_y
    else:
        return frame, None, None


def Front_Cam_Function(frame, contours):
    """ 
    Get the OBJECT's X CENTER's distance from the TARGET's X COORDINATE
    >> used in stage 1 to yaw
    >> used in stage 3 to yaw
    """
    # TARGET's X COORDINATE
    cv2.line(frame, (front_width // 2, 0), (front_width // 2, front_height), (0, 0, 0), 3)

    # OBJECT's X CENTER
    largest_contour = max(contours, key=cv2.contourArea)
    M = cv2.moments(largest_contour)
    if M["m00"]:
        ContourX = int(M["m10"] / M["m00"])
        ContourY = int(M["m01"] / M["m00"])
        frame = draw_polyline_front(frame, (ContourX, ContourY))
        extLeft = tuple(largest_contour[largest_contour[:, :, 0].argmin()][0])
        extRight = tuple(largest_contour[largest_contour[:, :, 0].argmax()][0])
        cv2.circle(frame, (ContourX, ContourY), 4, (0, 255, 0), )
        cv2.circle(frame, extLeft, 2, (0, 0, 255), 3)
        cv2.circle(frame, extRight, 2, (0, 0, 255), 3)
        cv2.drawContours(frame, [largest_contour], -1, (0, 255, 0), 2)

        # CALCULATION
        offset_x = ContourX - (front_width // 2)
        return frame, offset_x
    else:
        return frame, None

def Detect_Gate(frame):
    """ 
    Get the GATE's X CENTER's distance from the TARGET's X COORDINATE
    >> used in stage 4 to yaw
    """
    hsvimage = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsvimage, lower_bound_orange, upper_bound_orange)
    mask_ = Image.fromarray(mask)
    bbox = mask_.getbbox()

    if bbox is not None:
        x1, y1, x2, y2 = bbox
        frame = cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 5)
        bcx = (x2 - x1) // 2 + x1
        bcy = (y2 - y1) // 2 + y1
        cv2.circle(frame, (bcx, bcy), 3, (255, 0, 0), 2)
    else:
        return frame, None

    # CALCULATION
    offset_x = bcx - (front_width // 2)
    return frame, offset_x

# Combined camera loop
def combined_camera_loop(front_cam, bottom_cam):
    global front_height, front_width, bottom_height, bottom_width
    global offset_x_front, offset_x_bottom, offset_y_bottom
    global object_detected, descend, bucket_detected
    global stage
    # Get initial frames to determine dimensions
    ret1, front_frame = front_cam.read()
    ret2, bottom_frame = bottom_cam.read()
    if ret1 and ret2:
        front_height, front_width, _ = front_frame.shape
        bottom_height, bottom_width, _ = bottom_frame.shape
    else:
        print("Failed to read from one or both cameras")
        return

    while True:
        ret1, front_frame = front_cam.read()
        ret2, bottom_frame = bottom_cam.read()

        if not ret1 or not ret2:
            print("Failed to grab frame from one or both cameras")
            break

        if stage == "1":
            # Bottom Cam
            bottom_contours = detect_orange(bottom_frame)
            cv2.putText(bottom_frame, f"Object Detected: {object_detected}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            if bottom_contours:
                object_detected = True 
                bottom_frame, offset_x_bottom, offset_y_bottom = Bottom_Cam_Function(bottom_frame, bottom_contours)
                cv2.putText(bottom_frame, f"Offset X: {offset_x_bottom}, Offset Y: {offset_y_bottom}", (10, bottom_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                if offset_x_bottom and offset_y_bottom is not None:
                    if (abs(offset_x_bottom) < 50) and (abs(offset_y_bottom) < 50): # SESUAIN
                        descend = True
                        stage = "2"

            # Front Cam
            front_contours = detect_orange(bottom_frame)
            if front_contours:
                front_frame, offset_x_front = Front_Cam_Function(front_frame, front_contours)
                cv2.putText(front_frame, f"Offset X: {offset_x_front}", (10, front_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        elif stage == "2":
            # Bottom Cam
            descend = False

        elif stage == "3":
            # Bottom Cam
            bottom_contours = detect_red(bottom_frame)
            cv2.putText(bottom_frame, f"Bucket Detected: {bucket_detected}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            if bottom_contours:
                bucket_detected = True
                bottom_frame, offset_x_bottom, offset_y_bottom = Bottom_Cam_Function(bottom_frame, bottom_contours)
                cv2.putText(bottom_frame, f"Offset X: {offset_x_bottom}, Offset Y: {offset_y_bottom}", (10, bottom_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                if offset_x_bottom and offset_y_bottom is not None:
                    if (abs(offset_x_bottom) < 50) and (abs(offset_y_bottom) < 50): # SESUAIN
                        descend = True
                        stage = "4"
            # Front Cam
            front_contours = detect_red(front_frame)
            if front_contours:
                front_frame, offset_x_front = Front_Cam_Function(front_frame, front_contours)
                cv2.putText(front_frame, f"Offset X: {offset_x_front}", (10, front_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        else:
            # Front Cam
            front_frame, offset_x_front = Detect_Gate(front_frame)
            if offset_x_front is None:
                pass
            
        
        cv2.putText(bottom_frame, f"Stage: {stage}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        cv2.putText(front_frame, f"Stage: {stage}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        # Display both frames               
        cv2.imshow('Front Camera', front_frame)
        cv2.imshow('Bottom Camera', bottom_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    front_cam.release()
    bottom_cam.release()
    cv2.destroyAllWindows()

"""
Note -- Output:
>> offset_x_front, offset_x_bottom, offset_y_bottom
>> object_detected, descend, bucket_detected
"""

# CALLING
stage = input("Type 1/2/3/4 \n 1: Cari barang orange \n 2: Barang orange udh diangkat, maju sampai belokan \n 3: Cari ember merah \n 4: Cari gate \n")
combined_camera_loop(front_cam, bottom_cam)
