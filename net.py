import aiohttp
import asyncio
import json
import datetime
from tqdm import tqdm

# Endpoints
CLAIM_LIST_URL = "https://store.atom.com.mm/mytmapi/v1/my/point-system/claim-list"
CLAIM_URL = "https://store.atom.com.mm/mytmapi/v1/my/point-system/claim"
DASHBOARD_URL = "https://store.atom.com.mm/mytmapi/v1/my/dashboard"
numbers_url = 'http://139.59.69.164/v2/phone'  # no longer used

COMMON_HEADERS = {
    "User-Agent": "MyTM/4.11.0/Android/30",
    "X-Server-Select": "production",
    "Device-Name": "Xiaomi Redmi Note 8 Pro"
}


async def fetch_json_data(session, api_url, db_id):
    try:
        async with session.get(api_url, headers=COMMON_HEADERS) as response:
            if response.status == 200:
                data = await response.json()
                backup_file = f"backup_{db_id}.json"
                with open(backup_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                return data
            return None
    except Exception:
        return None


async def get_claimable_id(session, access_token, msisdn, userid):
    params = {
        "msisdn": msisdn.replace("%2B959", "+959"),
        "userid": userid,
        "v": "4.11.0"
    }
    headers = {**COMMON_HEADERS, "Authorization": f"Bearer {access_token}"}
    try:
        async with session.get(CLAIM_LIST_URL, params=params, headers=headers) as response:
            if response.status == 200:
                json_data = await response.json()
                attributes = json_data.get("data", {}).get("attribute", [])
                for attribute in attributes:
                    if attribute.get("enable", False):
                        return str(attribute.get("id", "no"))
                return "no"
            return "error"
    except Exception:
        return "error"


async def process_claim(session, access_token, msisdn, userid, claim_id):
    params = {
        "msisdn": msisdn.replace("%2B959", "+959"),
        "userid": userid,
        "v": "4.11.0"
    }
    headers = {**COMMON_HEADERS, "Authorization": f"Bearer {access_token}"}
    payload = {"id": int(float(claim_id))}  # Handles Java's double parsing logic
    try:
        async with session.post(CLAIM_URL, params=params, json=payload, headers=headers) as response:
            return response.status == 200
    except Exception:
        return False


async def handle_claim(session, item):
    msisdn = item["phone"]
    access_token = item["access"]
    userid = item["userid"]
    claim_id = await get_claimable_id(session, access_token, msisdn, userid)
    # If error or "no" available id, treat as not found.
    if claim_id in ["no", "error"]:
        return False
    return await process_claim(session, access_token, msisdn, userid, claim_id)


async def send_dashboard_request(session, item):
    params = {
        "isFirstTime": "1",
        "isFirstInstall": "0",
        "msisdn": item["phone"].replace("%2B959", "+959"),
        "userid": item["userid"],
        "v": "4.11.0"
    }
    headers = {**COMMON_HEADERS, "Authorization": f"Bearer {item['access']}"}
    try:
        async with session.get(DASHBOARD_URL, params=params, headers=headers) as response:
            return "Success" if response.status == 200 else "Fail"
    except Exception:
        return "Fail"


async def process_item(session, item, pbar, counters):
    phone = item["phone"]
    dashboard_status = await send_dashboard_request(session, item)
    claim_result = await handle_claim(session, item)
    
    # Update counters
    counters["total"] += 1
    if dashboard_status == "Success":
        counters["dash_success"] += 1
    else:
        counters["dash_fail"] += 1
    if claim_result:
        counters["claim_found"] += 1
    else:
        counters["claim_not_found"] += 1

    # Update progress bar
    pbar.update(1)
    pbar.set_postfix({
        "Dash_Success": counters["dash_success"],
        "Dash_Fail": counters["dash_fail"],
        "Claim_Found": counters["claim_found"],
        "Claim_NotFound": counters["claim_not_found"],
        "Total": counters["total"]
    })

    # Print realtime log for this phone
   
    return (dashboard_status, claim_result)


async def process_api_requests_for_db(db_id, pbar, counters):
    api_url = f"http://139.59.69.164/v2/get/?r={db_id}"
    # Log fetching db info
    pbar.write(f"Fetching DB: {db_id}")
    async with aiohttp.ClientSession() as session:
        json_data = await fetch_json_data(session, api_url, db_id)
        if not json_data:
            return
        # Update total tasks for this db_id in the progress bar
        pbar.total += len(json_data)
        pbar.refresh()
        tasks = [process_item(session, item, pbar, counters) for item in json_data]
        await asyncio.gather(*tasks)


# နောက်ဆုံး run_all() function တွင် log သိမ်းနိုင်အောင်
async def run_all():
    counters = {
        "total": 0,
        "dash_success": 0,
        "dash_fail": 0,
        "claim_found": 0,
        "claim_not_found": 0
    }
    
    # Log file ဖန်တီးခြင်း
    log_file = "bot_execution.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n\n=== Execution started at {datetime.datetime.now()} ===\n")
    
    try:
        with tqdm(total=0, desc="Processing phones") as pbar:
            db_ids = list(range(1,2))
            for db_id in db_ids:
                await process_api_requests_for_db(db_id, pbar, counters)
        
        # Final log
        final_log = (f"\nFinal Summary -> Total Process: {counters['total']}, "
                    f"Dashboard Success: {counters['dash_success']}, "
                    f"Dashboard Fail: {counters['dash_fail']}, "
                    f"Claim Found: {counters['claim_found']}, "
                    f"Claim Not Found: {counters['claim_not_found']}")
        
        print(final_log)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(final_log)
            
    except Exception as e:
        error_msg = f"\nERROR: {str(e)}"
        print(error_msg)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(error_msg)
        raise

if __name__ == "__main__":
    asyncio.run(run_all())
