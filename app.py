
import requests
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import google.generativeai as genai


app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_chats(filename, start_date, start_time, end_date, end_time):
    start_datetime = datetime.strptime(
        f"{start_date} {start_time}", "%d/%m/%Y %H:%M")
    end_datetime = datetime.strptime(
        f"{end_date} {end_time}", "%d/%m/%Y %H:%M")

    chats = {}
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split(' - ')
            if len(parts) >= 2:
                try:
                    timestamp = datetime.strptime(parts[0], "%d/%m/%Y, %H:%M")
                except ValueError:
                    continue  # Skip lines that don't contain a valid timestamp
                # Split only at the first occurrence of ':'
                user_message_parts = parts[1].split(':', 1)
                user = user_message_parts[0].strip()
                message = user_message_parts[1].strip() if len(
                    user_message_parts) > 1 else ''
                if start_datetime <= timestamp <= end_datetime:
                    if user not in chats:
                        chats[user] = []
                    chats[user].append(message)
    return chats


def detect_emotion(messages):
    GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)
    prompt = f"Analyze the conversation below and identify the prevailing emotions expressed by the participants. Provide insights into their emotional states, highlighting any shifts or nuances in feelings throughout the interaction. Your response should include the percentage breakdown of emotions such as sadness, happiness, anger, surprise, etc., to capture the emotional dynamics accurately. your response should be in a percentage format like 1)sad- 10% 2)happy- 20% like this that's it no description should be there. following are the parameters of response sadness, happyness, confusion, neutral, anger, surprise. Dont add any other thing. The messages are {messages}"
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return {'error': str(e)}


@app.route('/', methods=['GET'])
def index():
    return "Hello, World!"


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    start_date = request.form['start_date']
    start_time = request.form['start_time']
    end_date = request.form['end_date']
    end_time = request.form['end_time']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file and allowed_file(file.filename):
        # Create the uploads directory if it doesn't exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], "input.txt"))
        filename = "input.txt"
        chats = extract_chats(os.path.join(
            app.config['UPLOAD_FOLDER'], filename), start_date, start_time, end_date, end_time)

        # Detect emotion for each user's messages
        emotion_result = {}
        for user, messages in chats.items():
            print(messages)
            emotion_result[user] = detect_emotion(messages)

        # Include emotion result in the response JSON
        response = {'chats': chats, 'emotion': emotion_result}
        return jsonify(response)
    else:
        return jsonify({'error': 'Invalid file format'})


if __name__ == '__main__':
    app.run(threaded=True, debug=True, host="0.0.0.0", port=3000)
