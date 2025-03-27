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
                    json.dump(data, f, indent=4, ensure_ascii=False)
                return data
            return None
    except Exception as e:
        print(f"Error fetching data for DB {db_id}: {str(e)}")
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
    except Exception as e:
        print(f"Error getting claimable ID for {msisdn}: {str(e)}")
        return "error"

async def process_claim(session, access_token, msisdn, userid, claim_id):
    params = {
        "msisdn": msisdn.replace("%2B959", "+959"),
        "userid": userid,
        "v": "4.11.0"
    }
    headers = {**COMMON_HEADERS, "Authorization": f"Bearer {access_token}"}
    payload = {"id": int(float(claim_id))}
    try:
        async with session.post(CLAIM_URL, params=params, json=payload, headers=headers) as response:
            return response.status == 200
    except Exception as e:
        print(f"Error processing claim for {msisdn}: {str(e)}")
        return False

async def handle_claim(session, item):
    msisdn = item["phone"]
    access_token = item["access"]
    userid = item["userid"]
    claim_id = await get_claimable_id(session, access_token, msisdn, userid)
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
    except Exception as e:
        print(f"Error sending dashboard request for {item['phone']}: {str(e)}")
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

    return (dashboard_status, claim_result)

async def process_api_requests_for_db(db_id, pbar, counters):
    api_url = f"http://139.59.69.164/v2/get/?r={db_id}"
    pbar.write(f"Fetching DB: {db_id}")
    async with aiohttp.ClientSession() as session:
        json_data = await fetch_json_data(session, api_url, db_id)
        if not json_data:
            return
        pbar.total += len(json_data)
        pbar.refresh()
        tasks = [process_item(session, item, pbar, counters) for item in json_data]
        await asyncio.gather(*tasks)

async def run_all():
    start_time = datetime.datetime.now()
    counters = {
        "total": 0,
        "dash_success": 0,
        "dash_fail": 0,
        "claim_found": 0,
        "claim_not_found": 0
    }
    
    # Create output directory if not exists
    os.makedirs("output", exist_ok=True)
    
    with tqdm(total=0, desc="Processing phones", dynamic_ncols=True) as pbar:
        db_ids = list(range(1, 2))  # db_id 1 through 30
        for db_id in db_ids:
            await process_api_requests_for_db(db_id, pbar, counters)
    
    # Prepare final results
    end_time = datetime.datetime.now()
    results = {
        "metadata": {
            "script_version": "1.0",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds()
        },
        "statistics": {
            "total_processed": counters["total"],
            "success_rate": f"{(counters['dash_success']/counters['total'])*100:.2f}%" if counters['total'] > 0 else "0%"
        },
        "results": {
            "dashboard": {
                "success": counters["dash_success"],
                "fail": counters["dash_fail"]
            },
            "claims": {
                "found": counters["claim_found"],
                "not_found": counters["claim_not_found"]
            }
        }
    }
    
    # Save to JSON file
    output_file = f"output/results_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nFinal results saved to {output_file}")
    print(f"Total Processed: {counters['total']}")
    print(f"Dashboard Success: {counters['dash_success']} | Fail: {counters['dash_fail']}")
    print(f"Claims Found: {counters['claim_found']} | Not Found: {counters['claim_not_found']}")

if __name__ == "__main__":
    import os
    asyncio.run(run_all())
