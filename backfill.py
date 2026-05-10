import sqlite3
import time
import requests
from src.config import DB_PATH

def run_public_backfill():
    print("Connecting to local database...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Grab ALL posts that currently have 0 likes
    cur.execute("SELECT post_uri FROM post WHERE like_count = 0")
    posts = cur.fetchall()
    total_posts = len(posts)

    if total_posts == 0:
        print("No posts need updating! Exiting.")
        return

    print(f"Starting public API backfill for {total_posts} posts...")

    # The API allows a maximum of 25 URIs per request
    chunk_size = 25
    successful_updates = 0
    
    for i in range(0, total_posts, chunk_size):
        chunk = posts[i:i + chunk_size]
        
        # Construct the API URL. The public API requires URIs passed as query parameters.
        base_url = "https://public.api.bsky.app/xrpc/app.bsky.feed.getPosts"
        params = [('uris', post[0]) for post in chunk]
        
        try:
            # Ping the public, unauthenticated Bluesky server
            response = requests.get(base_url, params=params)
            
            # Rate Limit Failsafe
            if response.status_code == 429:
                print("Warning: Hit a rate limit! Pausing for 60 seconds to cool down...")
                time.sleep(60)
                continue
                
            response.raise_for_status()
            data = response.json()
            
            # Update SQLite with the fresh JSON data
            for bsky_post in data.get('posts', []):
                cur.execute("""
                    UPDATE post 
                    SET like_count = ?, reply_count = ?, repost_count = ?, quote_count = ?
                    WHERE post_uri = ?
                """, (
                    bsky_post.get('likeCount', 0), 
                    bsky_post.get('replyCount', 0), 
                    bsky_post.get('repostCount', 0), 
                    bsky_post.get('quoteCount', 0), 
                    bsky_post.get('uri')
                ))
            
            conn.commit()
            successful_updates += len(chunk)
            
            print(f"Progress: [{successful_updates}/{total_posts}] posts updated...")
            
            
            time.sleep(0.2) 

        except Exception as e:
            print(f"Error fetching chunk starting at index {i}: {e}")
            
            time.sleep(5)

    conn.close()
    print(f"\n--- Backfill Complete! Successfully updated {successful_updates} posts. ---")

if __name__ == "__main__":
    run_public_backfill()