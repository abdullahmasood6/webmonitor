import schedule
import time
import requests
import json
import logging
from urllib.parse import urlparse
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Suppress InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('website_monitoring.log'),
        logging.StreamHandler()
    ]
)

def check_website_status(url):
    headers = {
        'User-Agent': 'PostmanRuntime/7.39.0',
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'x-nlok-request-id': 'c6411622-e92c-4903-8870-7fe8dd69c513',
    }

    try:
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        end_time = time.time()
        response_time = end_time - start_time

        if response.status_code == 404:
            return False, f"404 Not Found - The requested resource was not found on this server. Response time: {response_time:.2f} seconds"
        elif response.status_code == 503:
            return False, f"503 Service Unavailable - The server cannot handle the request. Response time: {response_time:.2f} seconds"
        
        response.raise_for_status()
        return True, f"Website is up and running. Status code: {response.status_code}. Response time: {response_time:.2f} seconds"
    except requests.exceptions.HTTPError as e:
        return False, f"HTTP error occurred: {e}. Response time: {time.time() - start_time:.2f} seconds"
    except requests.exceptions.ConnectionError as e:
        return False, f"Connection error occurred: {e}"
    except requests.exceptions.Timeout as e:
        return False, f"Timeout occurred: {e}"
    except requests.exceptions.RequestException as e:
        return False, f"An error occurred: {e}"

def load_urls_from_json(filepath):
    with open(filepath, 'r') as file:
        data = json.load(file)
    return data['urls']

def load_email_template(filepath):
    with open(filepath, 'r') as file:
        return json.load(file)

def send_email_alert(subject, body):
    sender_email = "******"
    receiver_email = "*****"
    password = "********"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(message)
            logging.info(f"Alert email sent: {subject}")
    except Exception as e:
        logging.error(f"Failed to send email alert: {e}")

def job():
    logging.info("Running scheduled check...")
    urls = load_urls_from_json('urls.json')
    down_websites = []

    for url_info in urls:
        url = url_info['url']
        logging.info(f"\nChecking URL: {url}")
        website_alive, website_message = check_website_status(url)
        logging.info(f"Website check: {website_message}")

        if not website_alive:
            down_websites.append(f"{url}: {website_message}")

    # Load email template
    email_template = load_email_template('email_template.json')
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Prepare email content
    email_subject = email_template['subject'].format(date=current_date)
    down_websites_summary = "\n".join(down_websites) if down_websites else "All websites are up and running."
    email_body = email_template['body'].format(
        date=current_date,
        down_websites=down_websites_summary
    )

    # Send summary email only if there are down websites
    if down_websites:
        send_email_alert(email_subject, email_body)
        logging.info("Alert email sent for down websites.")
    else:
        logging.info("All websites are up. No alert email sent.")

def run_scheduler():
    schedule.every(1).minutes.do(job)
    logging.info("Scheduler started. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run_scheduler()
