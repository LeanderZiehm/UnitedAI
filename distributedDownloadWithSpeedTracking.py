import requests
import os
import time
import random
import socket
import uuid
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient
import csv
from downloadSpeedTracker import DownloadSpeedTracker

speed_tracker = DownloadSpeedTracker(window_sec=5)

load_dotenv()

uri = os.getenv("MONGO_URI")
client = MongoClient(uri)
db = client["arxiv"]
logs_collection = db["logs"]
links_collection = db["links_to_download"]
active_devices_collection = db["active_devices"]
downloads_collection = db["downloads"]

UTC = timezone.utc

def getTime():
    return datetime.now(UTC)

def log(message, level="INFO"):
    log_entry = {"timestamp": getTime(), "level": level, "message": message}
    logs_collection.insert_one(log_entry)
    print(message, getTime())

download_dir = "arxiv_papers"
os.makedirs(download_dir, exist_ok=True)

def load_user_agents(filename):
    user_agents = []
    with open(filename, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            user_agents.append(row["useragent"])
    return user_agents

def get_random_user_agent(filename):
    user_agents = load_user_agents(filename)
    return random.choice(user_agents) if user_agents else None

random_user_agent = get_random_user_agent("randomUserAgents.csv")
headers = {"User-Agent": random_user_agent}

device_id = str(uuid.uuid4())  
hostname = socket.gethostname()

active_devices_collection.update_one(
    {"device_id": device_id},
    {"$set": {"device_id": device_id, "hostname": hostname, "last_heartbeat": getTime()}},
    upsert=True
)

start_time = time.time()
CONSECUTIVE_403_THRESHOLD = 6
consecutive_403_count = 0

while True:
    
    active_devices_collection.update_one(
        {"device_id": device_id},
        {"$set": {"last_heartbeat": getTime()}}
    )

    left = links_collection.count_documents({"processedAt": {"$exists": False}})

    print("left", left)

    if left == 0:
        break  

    next_unprocessed_link = links_collection.find_one_and_update(
        {"processedAt": {"$exists": False}},  
        {"$set": {"processedAt": datetime.utcnow()}},  
        return_document=True
    )

    if not next_unprocessed_link:
        break  

    link = next_unprocessed_link["link"]
    pdf_url = link.replace("/abs/", "/pdf/")
    paper_id = link.split("/")[-1]
    pdf_path = os.path.join(download_dir, f"{paper_id}.pdf")

    if os.path.exists(pdf_path):
        log(f"Skipping (already downloaded): {pdf_path}")
        links_collection.update_one(
            {"_id": next_unprocessed_link["_id"]},
            {"$set": {"processedAt": getTime(), "status_code": 200, "file_name": f"{paper_id}.pdf"}}
        )
        continue

    try:
        response = requests.get(pdf_url, headers=headers, timeout=10)

        if response.status_code == 200:
            with open(pdf_path, "wb") as file:
                file.write(response.content)

            links_collection.update_one(
                {"_id": next_unprocessed_link["_id"]},
                {"$set": {"processedAt": getTime(), "status_code": 200, "file_name": f"{paper_id}.pdf"}}
            )

            speed_tracker.record_download()
            current_speed = speed_tracker.getDownloadSpeed()

            downloads_collection.insert_one({"device_id": device_id, "timestamp": getTime()})

            lastCheck = getTime() - timedelta(seconds=5)
            global_download_count = downloads_collection.count_documents({"timestamp": {"$gte": lastCheck}})

            active_devices_count = active_devices_collection.count_documents(
                {"last_heartbeat": {"$gte": getTime() - timedelta(seconds=10)}}
            )

            elapsed_time = time.time() - start_time
            processed_count = links_collection.count_documents({"processedAt": {"$exists": True}})
            total_papers = links_collection.count_documents({})
            progress_percent = (processed_count / total_papers) * 100

            log(f"""
 +[SUCCESS] {link} Downloaded: {pdf_path}
 Progress: {processed_count}/{total_papers} ({progress_percent:.2f}%)
 Speed: 
   - Current (local): {current_speed:.2f} downloads
   - Global: {global_download_count:.2f} downloads
 Active Devices: {active_devices_count}
 Time elapsed: {elapsed_time:.2f} sec
""")

            consecutive_403_count = 0

        elif response.status_code == 403:
            log(f"\n ==== [403 BLOCKED]: {pdf_path}\n")
            consecutive_403_count += 1
            if consecutive_403_count >= CONSECUTIVE_403_THRESHOLD:
                log(f"Reached {CONSECUTIVE_403_THRESHOLD} consecutive 403 errors. Stopping download process.", "ERROR")
                break

        else:
            links_collection.update_one(
                {"_id": next_unprocessed_link["_id"]},
                {"$set": {"processedAt": getTime(), "status_code": response.status_code}}
            )
            log(f"{'-'*20}\n-[Error]: {link}  {response.status_code}]  {pdf_url}\n{'-'*20}")

    except requests.exceptions.RequestException as e:
        links_collection.update_one(
            {"_id": next_unprocessed_link["_id"]},
            {"$set": {"processedAt": getTime(), "status_code": 500, "error": str(e)}}
        )
        log(f"Error downloading {pdf_url}: {e}", "ERROR")

    sleep_time = random.uniform(1, 3)
    time.sleep(sleep_time)

total_successful = links_collection.count_documents({"status_code": 200})
total_failed = links_collection.count_documents({"processedAt": {"$exists": True}, "status_code": {"$ne": 200}})
total_elapsed = time.time() - start_time

log("\nDownload process complete!", "SUCCESS")
log(f"Total successful downloads: {total_successful}")
log(f"Total failed downloads: {total_failed}")
log(f"Total elapsed time: {total_elapsed:.2f} sec")

active_devices_collection.delete_one({"device_id": device_id})
