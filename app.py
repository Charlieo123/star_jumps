from flask import Flask, render_template, Response, request, jsonify
import cv2
import mediapipe as mp
import numpy as np
import requests

app = Flask(__name__)

# Initialize MediaPipe Pose model
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# Define constants for wrist and ankle distance thresholds
WRIST_DISTANCE_THRESHOLD = 0.35
ANKLE_DISTANCE_THRESHOLD = 0.15

star_jumps = 0
jump_out = False
reset_state = True
counting_started = False

cap = cv2.VideoCapture(0)

# Function to calculate Euclidean distance between two points
def calculate_distance(x1, y1, x2, y2):
    return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

# Function to notify the Node.js server with the current number of star jumps
def send_star_jump_count(star_jumps, user_name=None):
    try:
        # Ensure user_name is included if available
        payload = {'star_jumps': star_jumps}
        if user_name:
            payload['user_name'] = user_name
        
        response = requests.post('http://localhost:3000/update-star-jumps', json=payload)
        if response.status_code != 200:
            print(f"Failed to update server: {response.status_code}")
    except Exception as e:
        print(f"Error while updating server: {e}")


# Video streaming generator function
def generate_frames():
    global star_jumps, jump_out, reset_state, counting_started
    
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while True:
            success, frame = cap.read()
            if not success:
                break

            # Convert the frame to RGB for processing
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False

            # Perform pose detection
            results = pose.process(image)

            # Convert the image color back to BGR for OpenCV rendering
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            if results.pose_landmarks:
                # Extract landmarks
                landmarks = results.pose_landmarks.landmark

                # Get wrist and ankle coordinates
                left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
                right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
                left_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]
                right_ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]

                # Calculate wrist and ankle distances
                wrist_distance = calculate_distance(left_wrist.x, left_wrist.y, right_wrist.x, right_wrist.y)
                ankle_distance = calculate_distance(left_ankle.x, left_ankle.y, right_ankle.x, right_ankle.y)

                # Logic for counting star jumps
                if wrist_distance > WRIST_DISTANCE_THRESHOLD and ankle_distance > ANKLE_DISTANCE_THRESHOLD:
                    jump_out = True
                else:
                    jump_out = False

                # Manage state transitions
                if jump_out and reset_state:
                    counting_started = True
                    reset_state = False
                elif not jump_out and counting_started:
                    star_jumps += 1
                    send_star_jump_count(star_jumps)
                    reset_state = True
                    counting_started = False

                # Display the count of star jumps
                cv2.putText(image, f"Star Jumps: {star_jumps}", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 2)

            # Render pose landmarks on the frame
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            # Encode the frame for HTTP streaming
            ret, buffer = cv2.imencode('.jpg', image)
            frame = buffer.tobytes()

            # Yield the output frame in byte format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('index.ejs')

@app.route('/update-star-jumps', methods=['POST'])
def update_star_jumps():
    global star_jumps
    data = request.json
    star_jumps = data.get('star_jumps', 0)
    user_name = data.get('user_name')

    # Here you can add additional logic if needed
    # For example, save to a database or handle more complex scenarios

    return jsonify({'status': 'success', 'star_jumps': star_jumps})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
