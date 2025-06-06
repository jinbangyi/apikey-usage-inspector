#!/usr/bin/env python3
"""
Test script for the async TwitterAPI client
"""
import asyncio
import os
from src.twitterapi.oauth import Settings
from src.twitterapi.oauth.twitterapi import TwitterAPIClient

async def test_twitterapi():
    """Test the TwitterAPI client"""
    print("🔍 Testing async TwitterAPI client...")
    
    # Create settings
    settings = Settings(
        google_email=os.getenv("GOOGLE_EMAIL", "alter@nftgo.io"),
        google_password=os.getenv("GOOGLE_PASSWORD"),
        session_token=os.getenv("TWITTERAPI_SESSION_TOKEN")
    )
    
    print(f"📧 Google Email: {settings.google_email}")
    print(f"🔑 Session Token: {'✓ Set' if settings.session_token else '✗ Not set'}")
    print(f"🌐 Base URL: {settings.base_url}")
    print(f"⚙️ API Base URL: {settings.api_base_url}")
    
    try:
        async with TwitterAPIClient() as client:
            print("\n✅ TwitterAPI client initialized successfully")
            
            # Test 1: Get auth session
            print("\n🔐 Testing auth session...")
            auth_session = await client.get_auth_session()
            if auth_session:
                print(f"✅ Auth session successful")
                print(f"   User ID: {auth_session.user.get('id', 'N/A')}")
                print(f"   Access Token: {'✓ Available' if auth_session.accessToken else '✗ None'}")
            else:
                print("❌ Auth session failed")
                return
            
            # Test 2: Get user info
            print("\n👤 Testing user info...")
            user_info = await client.get_user_info()
            if user_info:
                print(f"✅ User info retrieved")
                ui = user_info.data.user_info
                print(f"   API Key: {ui.api_key}")
                print(f"   Credits: {ui.recharge_credits:,}")
                print(f"   Bonus Credits: {ui.unused_bonuses_credits:,}")
                print(f"   QPS: {ui.qps}")
            else:
                print("❌ User info failed")
                return
            
            # Test 3: Get metrics
            print("\n📊 Testing metrics...")
            metrics = await client.get_metrics()
            if metrics:
                print(f"✅ Metrics retrieved successfully")
                print(f"   Provider: {metrics.provider}")
                print(f"   Usage: {metrics.usage:,}")
                print(f"   Limit: {metrics.limit:,}")
                
                # Print full summary
                print("\n" + "="*60)
                await client.print_summary()
                
                return metrics
            else:
                print("❌ Metrics retrieval failed")
                return None
                
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return None

async def main():
    """Main test function"""
    print("🚀 Starting TwitterAPI async client test")
    print("="*60)
    
    # Check environment variables
    if not os.getenv("GOOGLE_PASSWORD"):
        print("⚠️  Warning: GOOGLE_PASSWORD environment variable not set")
        print("   OAuth flow will not work without credentials")
    
    metrics = await test_twitterapi()
    
    if metrics:
        print("\n🎉 All tests passed!")
        print(f"📈 Final metrics: {metrics.usage:,}/{metrics.limit:,}")
    else:
        print("\n❌ Tests failed!")
    
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
