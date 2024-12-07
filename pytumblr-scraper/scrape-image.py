import datetime
import requests
import shutil
import json
import pathlib
import os

oauth_consumer_key = "1RufIMnQ6RxycfF2rDxO1a41JaaDsfSwzMHkE4Ri19HgLd05HS"
secret_key = "gqSZZbOxmNSfTSXOantn1h8S15S2jftr4r4AbeqkjrHaWnOmKs"

"""
Request-token URL:
POST https://www.tumblr.com/oauth/request_token
Authorize URL:
https://www.tumblr.com/oauth/authorize
Access-token URL:
POST https://www.tumblr.com/oauth/access_token
"""


"""
Blog request example:
start with : "https://api.tumblr.com"
make a post on blog : "/v2/blog/{blog-identifier}/..."

full url : "https://api.tumblr.com/v2/blog/{blog-identifier}/..."
"""


# IMAGE DOWNLOADING FUNCTION
def download_image(
    url,
    image_name,
    image_directory,
):

    response = requests.get(url=url, stream=True)
    if response.status_code == 200:
        print("> Downloading image...")
        file_extension = url.split(".")[-1]
        filename = str(image_name) + "." + file_extension

        file_path = pathlib.Path(os.getcwd(), image_directory, filename)

        with open(file=file_path, mode="wb") as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response
        print("> Image downloaded successfully.")
        return 0
    else:
        print(f"> Error downloading the image file.")
        return 1


IMAGE_DLOAD_DIR = pathlib.Path(os.getcwd(), r"Small Programs/pytumblr-scraper/img/")
LOG_DIR =  pathlib.Path(os.getcwd(), r"Small Programs/pytumblr-scraper/log/")


blog_name = "aestheticanimegifs"
blog_url = f"{blog_name}.tumblr.com"
api_url = f"https://api.tumblr.com/v2/blog/{blog_url}/posts"
params = {"api_key": oauth_consumer_key}
headers = {"Content-Type": "application/json"}

print("> Sending API request...")
response = requests.get(api_url, params=params, headers=headers)

if response.status_code == 200:
    print("> Request made successfully.")
    file_path = pathlib.Path(
        os.getcwd(),LOG_DIR , "tumblr-response.json"
    )
    json_response = response.json()

    with open(file_path, "w") as json_file:
        print(f"> Saving response at {file_path}")
        json.dump(json_response, json_file)
        print("> Success.")

    resp_dict = dict(json_response)

    # Handle the response to get desired images from here on out
    response = resp_dict["response"]

    # INTIALISE FILE LOG

    curr_date = datetime.datetime.now().isoformat()
    dload_log = {"first_refresh": curr_date, "photos": {}}
    photo_log = dload_log['photos']

    # OLD FILE LOG
    dload_log_file_path = pathlib.Path(
        os.getcwd(), LOG_DIR ,"dload_log.json"
    )
    log_file_exists = os.path.exists(dload_log_file_path)

    if log_file_exists:
        with open(dload_log_file_path, "r") as dload_log_json:
            dload_log = dict(json.load(dload_log_json))
            photo_log = dload_log["photos"]

    # NEXT PAGE QUERY DETAILS
    first_refresh = dload_log["first_refresh"]
    last_refresh = datetime.datetime.fromisoformat(first_refresh)
    formatted_curr_date = datetime.datetime.fromisoformat(curr_date)
    days_passed = (last_refresh - formatted_curr_date).days

    # Next page get query URL
    next_page_query_url = response["_links"]['next']["href"]
    # Next page get query params
    next_page_query_param = response["_links"]['next']["query_params"]

    dload_log["next_url"] = next_page_query_url
    dload_log["next_query_params"] = next_page_query_param

    if days_passed >= 10:
        # GOTO NEXT PAGE
        next_page_url = dload_log["next_url"]
        nex_page_param = dload_log["next_query_params"]
        response_next = requests.get(url=next_page_url, params=nex_page_param)

        if response_next.status_code == 200:
            print("> Next request made successfully.")

            response = response_next
            file_path = pathlib.Path(
                os.getcwd(), LOG_DIR ,"tumblr-response.json"
            )
            json_response = response.json()

            with open(file_path, "w") as json_file:
                print(f"> Saving response at {file_path}")
                json.dump(json_response, json_file)
                print("> Success.")

            resp_dict = dict(json_response)

            # Handle the response to get desired images from here on out
            response = resp_dict["response"]

            # UPDATE THE LOG FILE
            dload_log["first_refresh"] = curr_date
            # Next page get query URL
            next_page_query_url = response["_links"]['next']["href"]
            # Next page get query params
            next_page_query_param = response["_links"]['next']["query_params"]

            dload_log["next_url"] = next_page_query_url
            dload_log["next_query_params"] = next_page_query_param

    # CURRENT PAGE DETAILS

    # Get total post count from response
    total_posts = response["total_posts"]

    # Get the posts from response
    posts = response["posts"]

    # DOWNLOAD PHOTOS

    photos_dloaded = 0
    max_dloads = 9
    for post in posts:
        if photos_dloaded >= max_dloads:
            break

        post_id = str(post["id"])

        is_photo = post["type"] == "photo"

        # If post is photo
        if is_photo:
            embedded_photos_in_post = post["photos"][0]
            orig_photo = embedded_photos_in_post["original_size"]
            orig_photo_url = orig_photo["url"]
            orig_photo_width = orig_photo["width"]
            orig_photo_height = orig_photo["height"]

        if log_file_exists and (post_id in dload_log):
            # If photo was fetched earlier
            continue
        else:
            # SEND DOWNLOAD REQUEST
            photo_response = requests.get(orig_photo_url)

            dload_status = download_image(
                url=orig_photo_url,
                image_name=post_id,
                image_directory=IMAGE_DLOAD_DIR,
            )
            if dload_status == 0:
                # Image downloaded and saved successfully
                photos_dloaded += 1

                # SAVE FILENAME AND ID in log
                photo_log[post_id] = str(orig_photo_url)

    # CLEANUP DLOAD LOG
    if len(dload_log) > 100:
        # Delete first 20 entries
        max_del = 20
        del_count = 0
        for key in dload_log:
            dload_log.pop(key, None)
            del_count += 1
            if del_count == (max_del - 1):
                break

    # SAVE UPDATED LOG DICTIONARY
    with open(dload_log_file_path, "w") as dload_log_json:
        dload_log['photos'] = photo_log
        json.dump(dload_log, dload_log_json)

    # Complete
    print("> COMPLETE.")
else:
    print(f">[ERROR] An error occured while fetching the response.")
