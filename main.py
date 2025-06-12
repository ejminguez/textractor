from fastapi import FastAPI, File, UploadFile

import boto3
import os
import uuid
from tempfile import NamedTemporaryFile
from datetime import datetime
from mangum import Mangum  # 🧠 ASGI -> Lambda adapter


app = FastAPI()

# AWS clients
textract_client = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')
dynamo_table = dynamodb.Table('ExtractedDocuments')


def extract_text_from_textract(file_path: str):
    with open(file_path, 'rb') as doc:
        response = textract_client.detect_document_text(Document={'Bytes': doc.read()})

    return " ".join([block["Text"] for block in response["Blocks"] if block["BlockType"] == "LINE"])

def insert_text_into_dynamodb(text: str):

    item = {

        'document_id': str(uuid.uuid4()),
        'extracted_text': text,
        'uploaded_at': datetime.utcnow().isoformat()
    }
    dynamo_table.put_item(Item=item)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Document Text Extractor API!"}

@app.post("/upload")

async def upload_file(file: UploadFile):
    with NamedTemporaryFile(delete=False, dir="/tmp") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name


    extracted_text = extract_text_from_textract(tmp_path)
    insert_text_into_dynamodb(extracted_text)

    os.remove(tmp_path)


    return {

        "status": "success",
        "preview": extracted_text[:100] + "..."
    }


# 👇 This is the Lambda handler

handler = Mangum(app)

