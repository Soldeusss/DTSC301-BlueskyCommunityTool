import sqlite3
import pandas as pd
from config import DB_PATH

def run_basic_stats():
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT text, created_at, like_count, reply_count, repost_count, quote_count 
        FROM post
    """
    df = pd.read_sql(query, conn)
    conn.close()

    print(f"Total Posts Analyzed: {len(df)}")
    
    # Calculate Averages
    avg_likes = df['like_count'].mean()
    avg_replies = df['reply_count'].mean()
    print(f"\nAverage Likes per Post: {avg_likes:.2f}")
    print(f"Average Replies per Post: {avg_replies:.2f}")

    # Calculate Maximums (Finding the most viral posts)
    max_likes = df['like_count'].max()
    print(f"\nMost Viral Post Like Count: {max_likes}")

    # 3. Correlation Analysis
    # Does getting more replies mean you get more likes?
    correlation = df['like_count'].corr(df['reply_count'])
    print(f"\n--- Correlation Analysis ---")
    print(f"Correlation between Likes and Replies: {correlation:.3f}")
    
    if correlation > 0.7:
        print("Conclusion: Strong positive correlation. Highly debated posts get more likes.")
    elif correlation > 0.3:
        print("Conclusion: Moderate correlation.")
    else:
        print("Conclusion: Weak or no correlation.")
    
    print("\n--- Distribution Analysis---")
    median_likes = df['like_count'].median()
    print(f"Median Likes (The typical post): {median_likes}")

    # What does it take to be in the top 5% of all posts?
    top_5_percent_likes = df['like_count'].quantile(0.95)
    print(f"Top 5% Threshold: You need at least {top_5_percent_likes:.0f} likes to be in the top 5%.")

    print("\n--- Time-Series: Network Velocity ---")
    df['created_at'] = pd.to_datetime(df['created_at'], format='mixed', utc=True)
    
    # NEW: Filter out bad data (Only look at posts from 2024 onwards)
    clean_time_df = df[df['created_at'].dt.year >= 2024].copy()
    
    time_span = clean_time_df['created_at'].max() - clean_time_df['created_at'].min()
    print(f"Total time to ingest data: {time_span}")

    total_minutes = time_span.total_seconds() / 60
    if total_minutes > 0:
        posts_per_min = len(clean_time_df) / total_minutes
        print(f"Ingestion Velocity: {posts_per_min:.2f} posts per minute")

    print("\n--- Engagement Ratios ---")
    # Filter out posts with zero engagement to avoid dividing by zero
    engaged_posts = df[(df['like_count'] > 0) & (df['reply_count'] > 0)].copy()
    
    # Create a new column for the ratio
    engaged_posts.loc[:, 'reply_to_like_ratio'] = engaged_posts['reply_count'] / engaged_posts['like_count']
    
    avg_ratio = engaged_posts['reply_to_like_ratio'].mean()
    print(f"Average Reply-to-Like Ratio: {avg_ratio:.3f}")
    
    if avg_ratio > 0.5:
        print("Insight: High ratio. This implies a highly debated, conversational dataset.")
    else:
        print("Insight: Low ratio. This implies passive consumption (people like and scroll without arguing).")

if __name__ == "__main__":
    run_basic_stats()