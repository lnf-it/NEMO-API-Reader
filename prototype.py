"""
2026-06-15 Joseph Velez
This prototype retrieves NEMO API data from one or more API paths to provide a simple report.
Understanding the filters for a given API is essential.  I recommend opening the desired NEMO API; when it finishes loading, click "Filters". Ideally set a desired value and click Submit, but you can still get the filters by supplying any value.
"""
# Load libraries
import os
import sys
import argparse
import traceback
from argparse import ArgumentParser
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import math
from decimal import Decimal

import requests
from dotenv import load_dotenv
###########################################################
APP_NAME = "api_reader"
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"{APP_NAME}.log"
LOCK_FILE = LOG_DIR / f"{APP_NAME}.lock"
load_dotenv(ENV_PATH)
###########################################################
# Establish logging and locking functions
def get_previous_script_time():
    """ Read the previous script datetime from the log file.
        If a time cannot be found, return 24 hours ago.
        When a time is found, return 60 minutes ago."""
    now = datetime.now()
    ret = now - timedelta(days=1) # Default to 24 hours ago
    if not os.path.exists(LOG_FILE):
        return ret
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                if last_line:
                    # Extract datetime from log format: "2024-01-15 10:30:45 - Script ended"
                    parts = last_line.split(" - ")
                    if parts:
                        datetime_str = parts[0].strip()
                        ret = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S") - timedelta(minutes=60)
    except Exception as e:
        print(f"Error reading previous end time: {e}")
    return ret
def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
def acquire_lock():
    """Attempt to acquire the lock file. Return True if successful, False otherwise."""
    try:
        # Open lock file with exclusive access (os.O_CREAT | os.O_EXCL)
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except OSError:
        # Lock file already exists
        return False
def release_lock():
    """Remove the lock file."""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception as e:
        print(f"Error releasing lock: {e}")
def log_end_time():
    """Log the end datetime to the log file."""
    end_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{end_datetime} - Script ended\n")
        print(f"Script ended at {end_datetime}")
    except Exception as e:
        print(f"Error logging end time: {e}")

###########################################################
# Establish graceful connection closers
def gracefulClose(connection):
    try:
        connection.close()
    except:
        pass
# Establish API and record helpers
def fetch_api(session, base_url, api_path, params=None, silent=True):
    # Retrieves JSON data from NEMO and retuens a dictionary where key = JSON entry id, and value = dictionary of JSON key-value pairs.
    # NOTE: Python evaluates JSON values "", null, or false as False
    url = base_url.rstrip("/") + "/" + api_path.lstrip("/")
    r = session.get(url, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    ret = {item["id"]: item for item in data}
    if not silent: print("Fetched API", len(ret), api_path, params)
    datetime_keys = {} # NEMO uses ISO datetime format, not compatable with MySQL nor SQL. Normalize this data before using.
    if api_path == "/adjustment_requests": datetime_keys = {"creation_time", "last_updated", "original_start", "original_end", "new_start", "new_end"}
    if api_path == "/usage_events": datetime_keys = {"start", "end"}
    if api_path == "/reservations": datetime_keys = {"creation_time", "start", "end", "cancellation_time"}
    if api_path == "/scheduled_outages": datetime_keys = {"start", "end"}
    for rID,rRow in ret.items():
        for k in datetime_keys:
            if rRow.get(k) is not None: ret[rID][k] = datetime.fromisoformat(rRow[k]).replace(tzinfo=None, microsecond=0)
    return ret
def getRecordID(dct, srcKey, val):
    # For a given dictionary, return the record ID that contains a value in a specified key. May work unpredictably when that value is not unique.
    ret = None
    try:
        ret = next((k for k, v in dct.items() if v.get(srcKey) == val), None)
    except:
        pass
    return ret
def getRecordValue(dct, dID, srcKey, default=None):
    # For a given dictionary, use the provided dictionaryID to return the value of a specified key.
    # DictionaryID is established by the original fetch_api call. NEMO API defaults to the local "id" value.
    ret = default
    try:
        ret = dct[dID].get(srcKey, default)
    except:
        pass
    return ret
# Establish local helpers
def get_env(name, required=True, default=None):
    val = os.getenv(name, default)
    if required and not val:
        raise RuntimeError(f"Missing environment variable: {name}")
    return val
def get_duration(bDT, eDT):
    # Returns the number of seconds between bDT and eDT, or throws an unhandled error to let me know that something is very wrong.
    if eDT is None:
        diff_seconds = (datetime.now() - bDT).total_seconds()
        minutes = diff_seconds / 60
        return int(math.ceil(minutes / 15.0) * 15)
    return int((eDT - bDT).total_seconds() // 60)
def is_quarter(value: str | datetime) -> bool:
    if isinstance(value, str):
        value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return value.minute % 15 == 0 and value.second == 0
def time_softmatch(reservDT: datetime, eventDT: datetime) -> bool:
    #tolerance = timedelta(minutes=16)
    #return abs(seekDT - sourceDT) <= tolerance
    return (
        eventDT >= reservDT - timedelta(minutes=15)
        and eventDT < reservDT + timedelta(minutes=29)
    )
def difference(rowb, rowa):
    # Compares all keys in rowa against all matching values in rowb. Rowb is usually an xfer table row, and so has keys that rowa lacks.
    return all(
        key in rowa and rowb[key] == value
        for key, value in rowa.items()
    )
def timeframe_percentage_difference(oldBeginDateTime: datetime, oldEndDateTime: datetime, newBeginDateTime: datetime | None,newEndDateTime: datetime | None,) -> Decimal:

    # No updated values means no change.
    if newBeginDateTime is None and newEndDateTime is None: return Decimal("1")

    # Preserve the original boundary for whichever new value was omitted.
    if newBeginDateTime is None: newBeginDateTime = oldBeginDateTime
    if newEndDateTime is None: newEndDateTime = oldEndDateTime

    old_duration_seconds = Decimal(str((oldEndDateTime - oldBeginDateTime).total_seconds()))
    new_duration_seconds = Decimal(str((newEndDateTime - newBeginDateTime).total_seconds()))

    if old_duration_seconds == 0: raise ValueError("The old time frame cannot have a zero duration.")

    return new_duration_seconds / old_duration_seconds
def truncate(src, places=0):
    factor = 10 ** places
    return math.trunc(src * factor) / factor

###########################################################

###########################################################
    
def main():
    DRY_RUN = get_env("FLAG_DRY_RUN")
    
    # Establish process lock
    if not acquire_lock():
        print(f'Script is already running. Lock file exists: {LOCK_FILE}')
        sys.exit(1)
    print(f'Script started at {datetime.now()}.  DRY_RUN = {DRY_RUN}.')
    #------------------------------------------------------
    # Accommodate a forced start and end date
    dateStart = get_previous_script_time()
    dateEnd = datetime.now() + timedelta(days=14)
    parser = argparse.ArgumentParser()
    parser.add_argument("--datestart", type=parse_date, default=None, help="Override DateStart (YYYY-MM-DD)")
    parser.add_argument("--dateend", type=parse_date, default=None, help="Override DateEnd (YYYY-MM-DD)")
    args = parser.parse_args()
    if args.datestart is not None:
        dateStart = args.datestart
    if args.dateend is not None:
        dateEnd = args.dateend
    #------------------------------------------------------
    # BEGIN SCRIPT SPINE
    try:
        # Establish API session and database cursors
        api_session = requests.Session()
        api_base_url = get_env("API_URL")
        api_token = os.getenv("API_TOKEN")
        if api_token: api_session.headers.update({"Authorization": f'Token {api_token}'})
        
        #--------------------------------------------------
        print(f'dateStart: {dateStart}, dateEnd: {dateEnd}')
        print()        
        
        try:
            """ Use filter keys for best performance! An unfiltered fetch can take several minutes to complete.  
                Filters are applied in a local dictionary.
            """
            api_usage = fetch_api(api_session, api_base_url, "/usage_events", {"start__gte":{dateStart}, "start__lt":{dateEnd}})
            api_projects = fetch_api(api_session, api_base_url, "/projects", {"active":True})
            api_reserv = fetch_api(api_session, api_base_url, "/reservations", {"start__gte":{dateStart}, "start__lt":{dateEnd}})
            api_outage = fetch_api(api_session, api_base_url, "/scheduled_outages", {"start__gte":{dateStart}, "start__lt":{dateEnd}})
            api_tools = fetch_api(api_session, api_base_url, "/tools", {"visible":True})
            api_users = fetch_api(api_session, api_base_url, "/users", {"is_active":True})
            print()
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
            raise
    ###########################################################################
    # BEGIN SCRIPT CORE
        """ Loop results will appear in whatever order the REST framework provides. Use additional logic if a specific order is desired."""
        for usgID, usgRecord in api_usage.items():
            username = f'[User {usgID}]'
            userID = usgRecord.get("operator")
            if userID: username = f'{getRecordValue(api_users, userID, "last_name")}, {getRecordValue(api_users, userID, "first_name")}'
            
            project = getRecordValue(api_projects, usgRecord.get("project"), "name", f'[Project {usgRecord.get("project")}]')
            tool = getRecordValue(api_tools, usgRecord.get("tool"), "name", f'[Tool {usgRecord.get("tool")}]')
            startDT = usgRecord.get("start")
            endDT = usgRecord.get("end")
            
            print('----------------------------------------')
            print(f'Usage Event {usgID}')
            print(f'{username}\t\t{project}')
            print(f'\tStart: {startDT}')
            print(f'\tEnd  : {endDT}')
            print()
        
    
    # END SCRIPT CORE
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        raise
    finally:
        gracefulClose(api_session)
        release_lock()
        log_end_time()
    
if __name__ == "__main__":
    raise SystemExit(main())
