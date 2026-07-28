import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Loading environment variables from the .env file
load_dotenv()

# Initializing the Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_connection():
    try:
        # Querying a non-existent table to test connectivity
        result = supabase.table("products").select("*").limit(1).execute()
        return True, "Connected to Supabase!"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"