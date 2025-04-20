#!/usr/bin/env python3

import json
import sys
import os
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import subprocess
import time
from datetime import datetime

# Load settings
with open('settings.json', 'r') as f:
    settings = json.load(f)

# Load additional settings
try:
    with open('settings2.json', 'r') as f:
        settings2 = json.load(f)
except FileNotFoundError:
    print("settings2.json not found. Please create this file with email configuration.")
    settings2 = {
        "target_date": "30/04/2025",
        "email": {
            "enabled": False
        },
        "sleep_between_cycles_seconds": 3600
    }

# Parse target date
TARGET_DATE = datetime.strptime(settings2.get('target_date', '30/04/2025'), '%d/%m/%Y')

# Load centers
with open('docs/centers.json', 'r') as f:
    centers = json.load(f)

def send_email(center_name, appointment_date, center_id):
    """Send an email notification when an early appointment is found"""
    if not settings2.get('email', {}).get('enabled', False):
        print("Email notifications are disabled in settings2.json")
        return False
        
    # Email settings from settings2.json
    email_config = settings2.get('email', {})
    smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
    smtp_port = email_config.get('smtp_port', 587)
    smtp_username = email_config.get('smtp_username', '')
    smtp_password = email_config.get('smtp_password', '')
    email_recipient = email_config.get('recipient', '')
    email_subject = email_config.get('subject', 'Early RTA Appointment Found!')
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = email_recipient
    msg['Subject'] = email_subject
    
    body = f"""
    An early appointment has been found!
    
    Location: {center_name}
    Center ID: {center_id}
    Appointment Date: {appointment_date}
    
    This is earlier than your target date of {settings2.get('target_date', '30/04/2025')}.
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Send email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f"Email sent successfully for center {center_name}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def check_appointment_date(center_id, result_file):
    """Check if the appointment date for a center is before the target date"""
    python_exe = settings.get('python3_executable', 'python3')
    
    # Run the scrape_availability.py script
    try:
        subprocess.run([python_exe, 'scrape_availability.py', str(center_id), result_file], 
                      check=True)
        
        # Read the last line of the result file to get the most recent result
        with open(result_file, 'r') as f:
            lines = f.readlines()
            if not lines:
                return None  # No results
                
            last_line = lines[-1]
            result_data = json.loads(last_line)
            
            # Extract the next available date
            if 'result' in result_data and 'ajaxresult' in result_data['result']:
                slots = result_data['result']['ajaxresult'].get('slots', {})
                next_date = slots.get('nextAvailableDate')
                
                if next_date:
                    # Parse the date string
                    appointment_date = datetime.strptime(next_date, '%d/%m/%Y %H:%M')
                    
                    # Get center name from centers.json
                    center_name = None
                    for center in centers:
                        if str(center['id']) == str(center_id):
                            center_name = center['name']
                            break
                    
                    return {
                        'center_id': center_id,
                        'center_name': center_name,
                        'date': appointment_date,
                        'date_str': next_date
                    }
    except Exception as e:
        print(f"Error processing center {center_id}: {e}")
        # Add the failed center to errors file
        with open('errors.txt', 'a') as f:
            f.write(f"{center_id}\n")
            
    return None

def run_scraping_cycle():
    """Run a complete cycle of scraping all centers"""
    # Create or clear results file
    with open('results.json', 'w') as f:
        f.write('')
    
    # Create or clear errors file
    with open('errors.txt', 'w') as f:
        f.write('')
        
    print(f"{datetime.now().strftime('[%H:%M:%S] :')} Starting the early appointment check...")
    
    # Process each center
    found_early_appointment = False
    for center in centers:
        center_id = center['id']
        print(f"{datetime.now().strftime('[%H:%M:%S] :')} Checking center {center['name']} (ID: {center_id})...")
        
        appointment_info = check_appointment_date(center_id, 'results.json')
        
        if appointment_info and appointment_info['date'] < TARGET_DATE:
            print(f"EARLY APPOINTMENT FOUND at {appointment_info['center_name']}: {appointment_info['date_str']}")
            send_email(
                appointment_info['center_name'],
                appointment_info['date_str'],
                appointment_info['center_id']
            )
            found_early_appointment = True
        
        # Small delay between requests to avoid overloading the server
        time.sleep(2)
    
    # Process any errors
    error_count = 0
    with open('errors.txt', 'r') as f:
        error_ids = [line.strip() for line in f.readlines()]
        error_count = len(error_ids)
    
    while error_count > 0:
        print(f"{datetime.now().strftime('[%H:%M:%S] :')} Errors - {error_count}")
        # Rename errors.txt to errors_old.txt
        os.rename('errors.txt', 'errors_old.txt')
        
        # Create new errors.txt
        with open('errors.txt', 'w') as f:
            f.write('')
        
        # Process each error
        for center_id in error_ids:
            print(f"{datetime.now().strftime('[%H:%M:%S] :')} Retrying center ID: {center_id}...")
            
            appointment_info = check_appointment_date(center_id, 'results.json')
            
            if appointment_info and appointment_info['date'] < TARGET_DATE:
                print(f"EARLY APPOINTMENT FOUND at {appointment_info['center_name']}: {appointment_info['date_str']}")
                send_email(
                    appointment_info['center_name'],
                    appointment_info['date_str'],
                    appointment_info['center_id']
                )
                found_early_appointment = True
            
            # Small delay between requests
            time.sleep(2)
        
        # Check for new errors
        with open('errors.txt', 'r') as f:
            error_ids = [line.strip() for line in f.readlines()]
            error_count = len(error_ids)
    
    # Organize results for the UI
    if os.path.exists('results.json') and os.path.getsize('results.json') > 0:
        print(f"{datetime.now().strftime('[%H:%M:%S] :')} Reorganising results...")
        # Combine each line of results.json into a JSON array
        with open('results.json', 'r') as f:
            results = [json.loads(line) for line in f.readlines()]
        
        # Write to docs/results.json
        with open('docs/results.json', 'w') as f:
            json.dump(results, f)
        
        # Update timestamp
        with open('docs/update-time.txt', 'w') as f:
            f.write(datetime.now().strftime('%Y-%m-%d %H:%M%p'))
    
    # Clean up temp files
    if os.path.exists('errors_old.txt'):
        os.remove('errors_old.txt')
    
    # Git upload if enabled
    if settings.get('git_upload') == 'true':
        print(f"{datetime.now().strftime('[%H:%M:%S] :')} Pushing the latest data update back to github...")
        try:
            subprocess.run(['git', 'pull', '--depth=1'], check=True)
            subprocess.run(['git', 'add', './docs/results.json', './docs/update-time.txt'], check=True)
            subprocess.run(['git', 'commit', '-m', "data update"], check=True)
            subprocess.run(['git', 'push', '--quiet'], check=True)
        except Exception as e:
            print(f"Error pushing to git: {e}")
    
    print(f"{datetime.now().strftime('[%H:%M:%S] :')} All processes complete.")
    
    if found_early_appointment:
        print("Found at least one early appointment!")
    else:
        print("No early appointments found before {settings2.get('target_date', '30/04/2025')}.")
    
    return found_early_appointment

def main():
    """Main function that runs in a continuous loop"""
    cycle_count = 1
    
    try:
        while True:
            print(f"{datetime.now().strftime('[%H:%M:%S] :')} Starting cycle {cycle_count}")
            
            # Run a complete scraping cycle
            found_early = run_scraping_cycle()
            
            # Get sleep time between cycles
            sleep_seconds = settings2.get('sleep_between_cycles_seconds', 3600)
            
            print(f"{datetime.now().strftime('[%H:%M:%S] :')} Cycle {cycle_count} completed. Sleeping for {sleep_seconds} seconds...")
            cycle_count += 1
            
            # Sleep until next cycle
            time.sleep(sleep_seconds)
            
    except KeyboardInterrupt:
        print(f"{datetime.now().strftime('[%H:%M:%S] :')} Script stopped by user.")
    except Exception as e:
        print(f"{datetime.now().strftime('[%H:%M:%S] :')} Script stopped due to error: {e}")

if __name__ == "__main__":
    main() 