import requests
import os
import json
from time import sleep
from collections import deque
from pprint import pprint

# This whole thing gets detected under REMOTE API EVENT


# TODO: Convert into a Jdownloader class


def download_urls(dload_urls, DEST_FOLDER, JD_LOCALHOST=r"http://127.0.0.1:3128/"):
    local_dloader_address = JD_LOCALHOST

    # HACK: Check if Jdownloader is running
    dloader_status_url = local_dloader_address + "jdcheck.js"
    try:
        response = requests.get(dloader_status_url)
        # print("===" * 15)
        # print(f"> Downloader running status: {response.status_code}")
        # print("===" * 15)

    except Exception as e:
        print("===" * 15)
        print("> Possibly Jdownloader is not running!")
        print("===" * 15)
        print(e)
        return

    # HACK: Add a link and download if downloader is running
    if response.status_code == 200:
        print("===" * 15)
        # endpoint -> http://127.0.0.1:3128/linkgrabberv2/addLinks
        # body (not parameters) -> Python requests : data => body | params => paremeters
        add_links_url = JD_LOCALHOST + "linkgrabberv2/addLinks"
        dload_payload = {
            "params": [
                {
                    "assignJobID": True,
                    "autoExtract": False,
                    "autostart": True,
                    "deepDecrypt": False,
                    "destinationFolder": DEST_FOLDER,
                    "links": dload_urls,
                    "overwritePackagizerRules": True,
                    "priority": "DEFAULT",
                }
            ]
        }
        req_header = {"Content-Type": "application/json"}
        response = requests.post(
            url=add_links_url, json=dload_payload, headers=req_header
        )
        json_response = response.json()
        if response.status_code != 200:
            print("===" * 15)
            print(f"> Download request status: {response.status_code}")
            print(f"> Download request output: {json_response}")
            print("===" * 15)

        print("===" * 15)
        print(json_response)
        return (json_response["data"]["id"], response.status_code)

        # return None


# HACK: Function to regularly detect changes in a youtube playlist
def detect_playlist_changes(
    API_KEY, playlistId, LOCAL_PLAYLIST_DIR, JD_LOCALHOST=r"http://127.0.0.1:3128/"
) -> bool:
    request_endpoint_info = r"https://www.googleapis.com/youtube/v3/playlists"
    request_endpoint_items = r"https://www.googleapis.com/youtube/v3/playlistItems"

    payload = {
        "part": "snippet",
        "id": f"{playlistId}",
        "key": f"{API_KEY}",
        "fields": "items(snippet/title)",  # Comment to get extra information about playlist
    }

    req_header = {"referer": r"http://localhost:4444"}
    print("===" * 15)

    print("> Initiating playlist metadata get...")
    playlist_response = requests.get(
        request_endpoint_info, params=payload, headers=req_header
    )
    json_playlist_response = playlist_response.json()
    playlist_title = json_playlist_response["items"][0]["snippet"]["title"]

    print(f"> Requested playlist's title: {playlist_title}")

    payload = {
        "part": "snippet",
        "fields": "items(kind),items(snippet/title),items(snippet(resourceId/kind)),items(snippet(resourceId/videoId))",
        "playlistId": f"{playlistId}",
        "key": f"{API_KEY}",
        "maxResults": "50",
    }

    print("===" * 15)
    print("> Initiating playlist items GET...")

    response = requests.get(request_endpoint_items, params=payload, headers=req_header)
    json_response = response.json()

    print(f"> Request status: {response.status_code}")
    print("===" * 15)

    try:
        print("> Storing playlist items API response...", end="")
        with open(os.getcwd() + "\\response.json", "w") as f:
            f.write(json.dumps(json_response, indent=4))
        print("Complete.")
    except Exception as e:
        print("> An error occured while storing API resonse!")
    print("===" * 15)


    item_list = json_response["items"]
    item_count = 0
    video_count = 0

    playlist_path = LOCAL_PLAYLIST_DIR + f"\\{playlist_title}"
    if not (os.path.exists(playlist_path)):
        try:
            print("> Creating directory for playlist...", end="")
            os.mkdir(playlist_path)
            print("Complete.")
            print("===" * 15)
        except Exception as e:
            print("> An error occured while )creating dir for playlist!")
            print(e)

    erred_dloads = []
    added_dloads = deque([])

    print("> \tCOMMENCE PLAYLIST SYNC...")
    for item in item_list:
        print("+++" * 15)
        if item["kind"] == "youtube#playlistItem":
            item_snippet = item["snippet"]
            if item_snippet["resourceId"]["kind"] == "youtube#video":
                video_title = item_snippet["title"]
                video_id = item_snippet["resourceId"]["videoId"]
                video_path = playlist_path + f"\\{video_title}"


                if not (os.path.exists(video_path)):
                    video_url = "https://www.youtube.com/watch?v=" + video_id
                    print(f"> Downloading video [{video_title} : {video_url}]")

                    # Trigger download of above url in Jdownloader at video path
                    print("> Adding Link to downloader...", end="")
                    video_dload_jobId, status_code = download_urls(
                        dload_urls=video_url, DEST_FOLDER=video_path
                    )
                    if (status_code) != 200:
                        print(
                            f"> An error occured in downloading: [{video_title}: {video_dload_jobId}]"
                        )
                        erred_dloads.append(
                            {
                                "video_title": video_title,
                                "video_url": video_url,
                                "jobId": video_dload_jobId,
                            }
                        )
                    else:
                        added_dloads.append([video_dload_jobId, 1])
                        print("Done.")
                else:
                    print("> Video present at destination.")

                video_count += 1

            item_count += 1

    print("===" * 15)
    print("Waiting to begin link status check...", end="")
    sleep(25)
    print("complete. Starting now!")
    print("===" * 15)

    dloads_started = deque([])

    while added_dloads:
        print("> Scanning Link Grabber for pending items...")
        query_url = JD_LOCALHOST + "/linkgrabberv2/queryLinks"
        payload = {"queryParams": {"jobUUIDs": [str(added_dloads[0])]}}
        response = requests.get(query_url, params=json.dumps(payload))
        json_response = response.json()

        if response.status_code != 200:
            print("> Error scanning items in linkgrabber.")
        else:

            if len(json_response["data"]) > 0:
                # Item is still in linkgrabber
                round = added_dloads[0][1]
                round += 1
                if round > 2:
                    print("> Add provision to shift into force download.")
                    move_to_dload_list_url = JD_LOCALHOST + "/linkgrabberv2/moveToDownloadlist"
                    payload = {
                        "linkIds":[added_dloads[0][0]]
                    }
                    response = requests.get(move_to_dload_list_url, params=json.dumps(payload))
                    if response.status_code == 200:
                        print("> Add provision to handle error occuring")
                        # TODO: Add provision to handle items which are erroring out
                        # Add them to erred items and pop from added_dloads
                        erred_dload = added_dloads.popleft()
                        erred_dloads.append(erred_dload)
                else:
                    link = added_dloads.popleft()
                    added_dloads.append(link)
            else:
                # Job is not present in linkgrabber
                dloading = added_dloads.popleft()
                dloads_started.append(dloading)

    print("> Linkgrabber Empty.")
    print("===" * 15)
    print("> Beginning scan of downloader...")
    # Now check download list for presense of all items:
    while dloads_started:

        query_url = JD_LOCALHOST + "downloadsV2/queryLinks"
        payload = {
            "queryParams": {
                "availability": True,
                "bytesTotal": True,
                "enabled": True,
                "status": True,
                "bytesLoaded": True,
                "eta": True,
                "jobUUIDs": [dloads_started[0][0]],
                "finished": True,
            }
        }
        response = requests.get(query_url, params=json.dumps(payload))
        json_response = response.json()

        # print(response.status_code)
        # pprint(response.json())
        if response.status_code != 200:
            print("> Error scanning items in downloader.")
        else:
            sub_packages = json_response["data"]
            count_sub_total = len(sub_packages)


            for sub_package in sub_packages:
                if ("status" not in sub_package.keys()):
                    continue
                if (dloads_started[0][1] >= -1) and ((sub_package["status"]=="Download") or (sub_package["status"]=="Finished")):
                    count_sub_total -= 1
            
            dloads_started[0][1] -= 1
            if (count_sub_total == 0):
                # Download completed
                dloads_started.popleft()
            
            elif (count_sub_total != 0) and (dloads_started[0][1] < -1):
                # Put into errored category
                erred_dload = dloads_started.popleft()
                erred_dloads.append(erred_dload)
            else:
                # Give it one more chance
                retry_dload = dloads_started.popleft()
                dloads_started.append(retry_dload)


            

    print("> Sanity check complete!")

    print("+++" * 15)
    print("> \tPLAYLIST SYNC COMPLETE.")
    print("===" * 15)
    print("> Total playlist items: ", item_count)
    print("> Total videos in playlist: ", video_count)
    print("===" * 15)

    # # Check if video present on system or not:
    # for video in video_list:
    #     if os.path.exists("C:\\Users\\harsh\\Videos\\"):

    #         for root, dirs, files in os.walk("C:\\Users\\harsh\\Videos"):
    #             if

    return False


# TODO: Regularly perform downloads


# TODO: (OPTIONAL - BACKUP BEFORE PROCEEDING!)OVERHAUL TO HEAVY API USAGE
"""1.) do not use autostart
2.) wait for jobID to finish, via linkgrabberv2/queryLinkCrawlerJobs
3.) then query all link uuids from this job via linkgrabberv2/queryLinks and the jobID
4.) remove/manage those links (eg delete offline or other stuff)
5.) move those link uuids to download list via linkgrabberv2/moveToDownloadlist
6.) then you can start/manage your links
7.) then query all link uuids from this job via down downloadsV2/queryLinks via their uuids
8.) after downloads you can remove the links via downloadsV2/removeLinks and the link uuids
8.1) or use downloadsV2/cleanup
"""

if __name__ == "__main__":
    urls = r"https://www.fullvideos.xxx/get_file/8512/320ff449d0e2c50b9d4e5c579d08022febeb932712/93758000/93758142/93758142_720m.mp4/"
    API_KEY = r"AIzaSyAbfXRWxZ-EujvNmfHaFxE0TZgIOwmNr3g"
    # download_urls(dload_urls=urls, DEST_FOLDER="C:\\Users\\harsh\\Videos\\Youtube")
    # TEST PLAYLIST --> playlistID = r"PLAt1ye6EzsnsNPpE1njHtc7Yg8h2OKNT4"
    # playlistID = r"PLvkrU3vRXLfzaqM8QIK_NXPkhidjDdEMn" # Happy Place
    playlistID = r"PL3roRV3JHZzbatp5PvE-88ApmVishqGHN" # Happy Place
    LOCAL_PLAYLIST_LOCATION = "C:\\Users\\harsh\\Videos\\Youtube"
    detect_playlist_changes(API_KEY=API_KEY, playlistId=playlistID, LOCAL_PLAYLIST_DIR=LOCAL_PLAYLIST_LOCATION)
