import google_auth_oauthlib.flow
import googleapiclient.discovery
import datetime
import os
from googleapiclient.errors import HttpError

scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

def get_authenticated_service():
    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "client_secrets.json"

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    credentials = flow.run_local_server(port=0)
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)
    
    return youtube

def get_subscribed_channel_ids(youtube, user_channel_ids):
    subscribed_channel_ids = set()
    for user_channel_id in user_channel_ids:
        print(f"Fetching subscriptions for user channel ID: {user_channel_id}")
        try:
            request = youtube.subscriptions().list(
                part="snippet",
                channelId=user_channel_id,
                maxResults=500
            )
            response = request.execute()
            if 'items' in response:
                for item in response['items']:
                    subscribed_channel_ids.add(item['snippet']['resourceId']['channelId'])
            else:
                print(f"No subscriptions found for user channel ID: {user_channel_id}")
        except HttpError as e:
            print(f"An error occurred while fetching subscriptions: {e}")
    return list(subscribed_channel_ids)

def get_video_ids_by_channels(youtube, channel_ids, keywords=None, published_after=None):
    video_ids = []
    for channel_id in channel_ids:
        print(f"Searching videos for channel ID: {channel_id}")
        try:
            request = youtube.search().list(
                part="snippet",
                channelId=channel_id,
                maxResults=500,
                type="video",
                publishedAfter=published_after
            )
            if keywords:
                request.q = '|'.join(keywords)
            
            response = request.execute()
            if 'items' in response:
                for item in response['items']:
                    video_ids.append(item['id']['videoId'])
            else:
                print(f"No videos found for channel ID: {channel_id}")
        except HttpError as e:
            print(f"An error occurred while searching videos: {e}")
    return video_ids

def get_comments_by_user_and_videos(youtube, user_channel_ids, video_ids, max_requests=1000):
    comments = []
    request_count = 0

    for video_id in video_ids:
        if request_count >= max_requests:
            print("Reached maximum request limit.")
            break

        try:
            print(f"Fetching comments for video ID: {video_id}")
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100
            )
            response = request.execute()
            request_count += 1

            if 'items' in response:
                for item in response['items']:
                    comment = item['snippet']['topLevelComment']['snippet']
                    if comment['authorChannelId']['value'] in user_channel_ids:
                        comments.append(comment)
            else:
                print(f"No comments found for video ID: {video_id}")
        
        except HttpError as e:
            error_reason = e.resp.reason
            error_message = e.content.decode('utf-8')
            if 'commentsDisabled' in error_message:
                print(f"Comments are disabled for video ID {video_id}. Skipping this video.")
            else:
                print(f"An error occurred: {error_reason}")
                raise

    return comments

def save_comments_to_file(comments, filename):
    existing_comments = set()
    
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            existing_comments = set(file.read().splitlines())

    with open(filename, 'a', encoding='utf-8') as file:
        for comment in comments:
            comment_text = comment['textDisplay']
            if comment_text not in existing_comments:
                file.write(f"{comment}\n")
                existing_comments.add(comment_text)

if __name__ == "__main__":
    youtube = get_authenticated_service()
    
    user_channel_ids = ["UCEmRmaGIcLPw7bHVCY758ug"]  # Replace with actual user channel ID

    # Get subscribed channel IDs
    subscribed_channel_ids = get_subscribed_channel_ids(youtube, user_channel_ids)
    print(f"Subscribed channel IDs: {subscribed_channel_ids}")

    # Define specific channel IDs of media or channel users can post comments.
    channel_ids = [
        "UCW2QcKZiU8aUGg4yxCIditg", "UCfU2oLt2NnK9Te6NCN3UEJw", 
        "UCWvorN5uzvFhA7zJst6NKTg", "UCW5Jb8DlHXphrZVsXEWTVqg", 
        "UC16niRr50-MSBwiO3YDb3RA", "UCupvZG-5ko_eiXAupbDfxWw", 
        "UCNye-wNBqNL5ZzHSJj3l8Bg", "UCQfwfsi5VrQ8yKZ-UWmAEFg", 
        "UCSrZ3UV4jOidv8ppoVuvW9Q", "UCLLWAXn5F415g2kNAcE_T1g", 
        "UCI3RT5PGmdi1KVp9FG_CneA", "UCzKH70qfN_yuXq3s91fdwmg", 
        "UCOBMhI7TtRLTAGpcTjNvYCw", "UC75cGmLHmXN5oTK0nfYuBgA", 
        "UCVODHOG-e7SDwhzARSPAlEQ", "UCnhp5NblY_wOoQ7YIJJLWCQ", 
        "UCU08WO0NZldAswNY0ajTo2w", "UCbDTw0HZwrSL4BJRKdIwBKA",
        "UC6ZbGuT_zebhXkV-OeRzSoQ", 
    ]  # Replace with actual channel IDs

    keywords = ["Election 2024"] # will only take into account videos that have these keywords in their title, saving on API requests.
    published_after = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat("T") + "Z"

    # Search videos with keywords for specified channels
    video_ids_with_keywords = get_video_ids_by_channels(youtube, channel_ids, keywords, published_after)
    print(f"Found {len(video_ids_with_keywords)} videos matching keywords.")

    # Search videos without keywords for subscribed channels
    video_ids_subscribed_channels = get_video_ids_by_channels(youtube, subscribed_channel_ids, published_after=published_after)
    print(f"Found {len(video_ids_subscribed_channels)} videos from subscribed channels.")

    # Combine video IDs from both searches
    all_video_ids = video_ids_with_keywords + video_ids_subscribed_channels

    user_comments = get_comments_by_user_and_videos(youtube, user_channel_ids, all_video_ids)
    print(f"Found {len(user_comments)} comments by the user.")

    save_comments_to_file(user_comments, "user_comments.txt")
    print("Comments saved to user_comments.txt")


# "UCW2QcKZiU8aUGg4yxCIditg", "UCfU2oLt2NnK9Te6NCN3UEJw", "UCWvorN5uzvFhA7zJst6NKTg", "UCW5Jb8DlHXphrZVsXEWTVqg", "UCjOAgyDjdu7Bs5WP-9QOw6A", "UCh2HQFNwxuoSllzm_6VNLgg", "UCu89ejAME_UaPU9maI9Fv3Q", "UCUVCCoXAwqhBKmOLeBsFx-Q", 
# "UCYd42bFB4C5Jas8T1PwP_3w", "UC6g514xQshoWqsK_UMXl7_g", "UC1UVPmh1JLMrQYA4VWedsDA", "UCgn_8vm9IbMdmE_kkWy0ZmA", "UCckz6n8QccTd6K_xdwKqa0A", "UCW2QcKZiU8aUGg4yxCIditg", "UCfU2oLt2NnK9Te6NCN3UEJw", "UCWvorN5uzvFhA7zJst6NKTg", "UCW5Jb8DlHXphrZVsXEWTVqg", 
# "UC16niRr50-MSBwiO3YDb3RA", "UCupvZG-5ko_eiXAupbDfxWw", "UCNye-wNBqNL5ZzHSJj3l8Bg", "UCQfwfsi5VrQ8yKZ-UWmAEFg", "UCSrZ3UV4jOidv8ppoVuvW9Q", "UCLLWAXn5F415g2kNAcE_T1g", 
# "UCI3RT5PGmdi1KVp9FG_CneA", "UCzKH70qfN_yuXq3s91fdwmg", "UCOBMhI7TtRLTAGpcTjNvYCw", "UC75cGmLHmXN5oTK0nfYuBgA", "UCVODHOG-e7SDwhzARSPAlEQ", "UCnhp5NblY_wOoQ7YIJJLWCQ", 
# "UCU08WO0NZldAswNY0ajTo2w", "UCbDTw0HZwrSL4BJRKdIwBKA", "UC6ZbGuT_zebhXkV-OeRzSoQ", "UCYj6gXhcSTC65NBW2jj5UGw","UCW2QcKZiU8aUGg4yxCIditg", "UCuXUjhX7jCoOkX_0AymC1yw", "UCvcP_Oe2ap1Ks393FdHWA1A", "UChy3iek1clfWYBC8NP0u1vQ", "UCEmRmaGIcLPw7bHVCY758ug",
# "UCQ0wxwTxq_s5R27_O-yqeUA""UCW2QcKZiU8aUGg4yxCIditg", "UCfU2oLt2NnK9Te6NCN3UEJw", "UCWvorN5uzvFhA7zJst6NKTg", "UCW5Jb8DlHXphrZVsXEWTVqg", "UCjOAgyDjdu7Bs5WP-9QOw6A", "UCh2HQFNwxuoSllzm_6VNLgg", "UCu89ejAME_UaPU9maI9Fv3Q", "UCUVCCoXAwqhBKmOLeBsFx-Q", 
# "UCYd42bFB4C5Jas8T1PwP_3w", "UC6g514xQshoWqsK_UMXl7_g", "UC1UVPmh1JLMrQYA4VWedsDA", "UCgn_8vm9IbMdmE_kkWy0ZmA", "UCckz6n8QccTd6K_xdwKqa0A", "UCW2QcKZiU8aUGg4yxCIditg", "UCfU2oLt2NnK9Te6NCN3UEJw", "UCWvorN5uzvFhA7zJst6NKTg", "UCW5Jb8DlHXphrZVsXEWTVqg", 
# "UC16niRr50-MSBwiO3YDb3RA", "UCupvZG-5ko_eiXAupbDfxWw", "UCNye-wNBqNL5ZzHSJj3l8Bg", "UCQfwfsi5VrQ8yKZ-UWmAEFg", "UCSrZ3UV4jOidv8ppoVuvW9Q", "UCLLWAXn5F415g2kNAcE_T1g", 
# "UCI3RT5PGmdi1KVp9FG_CneA", "UCzKH70qfN_yuXq3s91fdwmg", "UCOBMhI7TtRLTAGpcTjNvYCw", "UC75cGmLHmXN5oTK0nfYuBgA", "UCVODHOG-e7SDwhzARSPAlEQ", "UCnhp5NblY_wOoQ7YIJJLWCQ", 
# "UCU08WO0NZldAswNY0ajTo2w", "UCbDTw0HZwrSL4BJRKdIwBKA", "UC6ZbGuT_zebhXkV-OeRzSoQ", "UCYj6gXhcSTC65NBW2jj5UGw","UCW2QcKZiU8aUGg4yxCIditg", "UCuXUjhX7jCoOkX_0AymC1yw", "UCvcP_Oe2ap1Ks393FdHWA1A", "UChy3iek1clfWYBC8NP0u1vQ",
