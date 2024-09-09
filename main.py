from flask import Flask, json, jsonify, request, send_file, Response
from flask_cors import CORS
from tasks import apiworld, img_process
import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import requests
import uuid
from io import BytesIO





app = Flask(__name__)
CORS(app)


mongo = MongoClient(os.environ.get("MONGO_URI"),server_api = ServerApi('1'))


from celery_config import celery_app
celery_app.autodiscover_tasks(['tasks'], force=True)


OUTPUT_FOLDER = "processed_images"

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

@app.route('/')
def index():
    return "OK"
    # return render_template('index.html')

@app.route('/apiworld')
def apiworld_route():
    task = apiworld.delay()
    print('Task Launched!')
    return jsonify({"success": True, "task_id": task.id})

@app.route('/check_task/<task_id>', methods=['GET'])
def check_task(task_id):
    # task = celery_app.AsyncResult(task_id)
    # print(f"Task {task_id} is currently in state: {task.state}")  # Print the task state
    if mongo.db.processed_images.find_one({"request_id": task_id}).get("status") == 'Success':
        # Assuming the task returns filename upon success
        response = jsonify({"status": "SUCCESS"})
        return response
    elif mongo.db.processed_images.find_one({"request_id": task_id}).get("status") == 'Pending':
        return jsonify({"status": "PENDING"})
    else:
        return jsonify({"status": "Failed"})


@app.route('/upload' , methods=['POST'])
def upload_csv():
    # Ensure the file part is in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    # Check if a file was selected
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    # Read CSV file content directly into memory
    csv_data = BytesIO(file.read())

    # Generate a unique request ID
    request_id = str(uuid.uuid4())

    # Insert initial record into MongoDB
    mongo.db.processed_images.insert_one({
        "request_id": request_id,
        "status": "Pending",
    })

    # Call the Celery task to process images, passing CSV data directly
    task = img_process.delay(request_id, csv_data.getvalue())

    return jsonify({"request_id": request_id}), 200

@app.route('/download/<request_id>', methods=['GET'])
def download_file(request_id):
    # Retrieve the document with the given request_id
    request_doc = mongo.db.processed_images.find_one({"request_id": request_id})

    if request_doc and "excel_file" in request_doc:
        # Create a BytesIO object from the binary data
        excel_binary = BytesIO(request_doc["excel_file"])

        # Send the file as an attachment
        return send_file(
            excel_binary,
            download_name=f"{request_id}_output.xlsx",
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        return Response("File not found or processing failed.", status=404)


# @app.route('/webhook/<request_id>', methods=['GET'])
# def webhook(request_id):
#     try:
#         # Make a request to the download endpoint for the request_id
#         download_url = f'http://localhost:5000/download/{request_id}'  # Replace with the correct URL
#         response = requests.get(download_url)
        
#         if response.status_code == 200:
#             # The file was successfully downloaded, process it as needed
#             print(f"Webhook called and download successful for request_id: {request_id}")
#         else:
#             print(f"Failed to download the file for request_id: {request_id}, Status code: {response.status_code}")

#     except Exception as e:
#         print(f"Error in webhook processing for request_id: {request_id} - {str(e)}")

#     return jsonify({"message": "Webhook processed"}), 200

@app.route('/webhook/imge', methods=['POST'])
def imge_webhook():
    data = request.json
    # logger.info('Received webhook data: %s', data)

    # Extract relevant information from the webhook data
    image_id = data.get('image_id')
    status = data.get('status')
    image_url = data.get('image_url')
    request_id = data.get('request_id')

    # Update MongoDB with the received data
    mongo.db.processed_images.update_one(
        {"request_id": request_id},
        {"$set": {"status": status, "image_url": image_url}}
    )

    return jsonify({'message': 'Webhook received'}), 200

    
    
if __name__ == '__main__':
    app.run(app,debug=True)