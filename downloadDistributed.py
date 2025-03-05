import requests
import os
import time
import random
from datetime import datetime, UTC
from dotenv import load_dotenv
from pymongo import MongoClient
import csv
import random



# Load environment variables
load_dotenv()

# Connect to MongoDB
uri = os.getenv("MONGO_URI")
client = MongoClient(uri)
db = client["arxiv"]
logs_collection = db["logs"]
links_collection = db["links_to_download"]

# Function to get current UTC time
def getTime():
    return datetime.now(UTC)


# Logging function
def log(message, level="INFO"):
    log_entry = {"timestamp": getTime(), "level": level, "message": message}
    logs_collection.insert_one(log_entry)
    print(message, getTime())

# Create download directory
download_dir = "arxiv_papers"
os.makedirs(download_dir, exist_ok=True)



# Load user agents from CSV
def load_user_agents(filename):
    user_agents = []
    with open(filename, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            user_agents.append(row["useragent"])
    return user_agents

# Pick a random user agent
def get_random_user_agent(filename):
    user_agents = load_user_agents(filename)
    return random.choice(user_agents) if user_agents else None

# Example usage
random_user_agent = get_random_user_agent("randomUserAgents.csv")

# Set headers with the random user agent
headers = {
    "User-Agent": random_user_agent
}

# Track progress
start_time = time.time()
CONSECUTIVE_403_THRESHOLD = 6
consecutive_403_count = 0

while True:
    # Get the number of remaining unprocessed links
    left = links_collection.count_documents({"processedAt": {"$exists": False}})

    print("left",left)
    
    if left == 0:
        break  # Stop when no unprocessed links are left

    # Get the next unprocessed link
    next_unprocessed_link = links_collection.find_one({"processedAt": {"$exists": False}})
    
    if not next_unprocessed_link:
        break  # Safety check: Exit if no more unprocessed links

    link = next_unprocessed_link["link"]
    pdf_url = link.replace("/abs/", "/pdf/")
    paper_id = link.split("/")[-1]
    pdf_path = os.path.join(download_dir, f"{paper_id}.pdf")

    # Check if file already exists
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

            elapsed_time = time.time() - start_time
            processed_count = links_collection.count_documents({"processedAt": {"$exists": True}})
            total_papers = links_collection.count_documents({})
            progress_percent = (processed_count / total_papers) * 100

            log(f"\n +[SUCCESS] {link} Downloaded: {pdf_path}\n Progress: {processed_count}/{total_papers} ({progress_percent:.2f}%) - Time elapsed: {elapsed_time:.2f} sec\n")
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

    # Random sleep to avoid rate-limiting
    sleep_time = random.uniform(1, 3)
    time.sleep(sleep_time)

# Final stats
total_successful = links_collection.count_documents({"status_code": 200})
total_failed = links_collection.count_documents({"processedAt": {"$exists": True}, "status_code": {"$ne": 200}})
total_elapsed = time.time() - start_time

log("\nDownload process complete!", "SUCCESS")
log(f"Total successful downloads: {total_successful}")
log(f"Total failed downloads: {total_failed}")
log(f"Total elapsed time: {total_elapsed:.2f} sec")
