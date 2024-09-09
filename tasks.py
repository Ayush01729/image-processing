import logging
from celery.utils.log import get_task_logger
from celery_config import celery_app
import time
from PIL import Image
import pandas as pd
from io import BytesIO, StringIO
import uuid
import os
import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import base64
import zlib



# for debugging purposes

logger = get_task_logger(__name__)
logger.setLevel(logging.INFO)  # Set logging level to INFO
handler = logging.FileHandler('my_log.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

OUTPUT_FOLDER = "processed_images"
# the task itself

mongo = MongoClient(os.environ.get("MONGO_URI"),server_api = ServerApi('1'))


@celery_app.task(name='tasks.img_process')
def img_process(request_id, csv_data):
    try:
        # Read CSV from in-memory data
        csv_string = BytesIO(csv_data)
        df = pd.read_excel(csv_string)
        output_data = []

        for _, row in df.iterrows():
            serial_number = row['S.No']
            product_name = row['Product Name']
            cleaned_image_urls = row['Input Image URLs'].split(',')
            input_image_urls = [url.strip() for url in cleaned_image_urls]

            output_image_urls = []
            for image_url in input_image_urls:
                try:
                    # Download the image from the URL
                    response = requests.get(image_url)
                    response.raise_for_status()  # Raise an exception for HTTP errors

                    # Open the image using PIL and compress it
                    img = Image.open(BytesIO(response.content))
                    output_io = BytesIO()
                    img.save(output_io, format='JPEG', quality=50)  # Compress image to 50% quality
                    output_bytes = output_io.getvalue()
                    compressed_data = zlib.compress(output_bytes)
                    path = base64.b64encode(compressed_data).decode('utf-8')
                    

                    # Upload the compressed image to im.ge
                    api_url = "https://im.ge/api/1/upload"
                    
                    headers = {'X-API-Key': 'imge_FJfS_0f7e46204eedc2adb831b9018d6138329b3af451313456d3ec0a4b86465398420192856b2141de0bde788e2460e546393107db1a37e516753e40a8b3311c8080'}
                    
                    params = { 'source': image_url , 
                                'format':'text'
                                } 
                    upload_response = requests.post(api_url , headers=headers , params=params)

                    # Ensure the upload was successful
                    upload_response.raise_for_status()
                    upload_data = upload_response.json()
                    if upload_data['status_code'] == 200:
                        # image_id = upload_data['image']['id']  # Extract the image ID
                        # uploaded_image_url = poll_image_status(image_id) 
                        uploaded_image_url = upload_data['image']['url']  # Extract the uploaded image URL
                        output_image_urls.append(uploaded_image_url)
                    else:
                        output_image_urls.append("Upload Failed")

                except Exception as e:
                    print(f"Error processing image {image_url}: {e}")
                    output_image_urls.append("Error")

            # Append processed data to the output list
            output_data.append({
                'S.No': serial_number,
                'Product Name': product_name,
                'Input Image URLs': ','.join(input_image_urls),
                'Output Image URLs': ','.join(output_image_urls),
            })

        # Convert data to DataFrame and Excel
        output_df = pd.DataFrame(output_data)
        output_excel = BytesIO()
        output_df.to_excel(output_excel, index=False)
        output_excel.seek(0)

        # Store Excel file as binary data in MongoDB
        mongo.db.processed_images.update_one(
            {"request_id": request_id},
            {
                "$set": {
                    "status": "Success",
                    "excel_file": output_excel.getvalue()
                }
            }
        )
        

    except Exception as e:
        # Handle errors and update status in MongoDB
        mongo.db.processed_images.update_one(
            {"request_id": request_id},
            {"$set": {"status": "Failed"}}
        )
        return str(e)






