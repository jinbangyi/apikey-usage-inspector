#!/usr/bin/env python3
"""
Test the TwitterAPI Settings and Metrics classes
"""
import os
from src.twitterapi.oauth import Settings
from src.settings import Metrics

def test_settings():
    """Test Settings class"""
    print("🔧 Testing Settings class...")
    
    # Test with environment variables
    os.environ["TWITTERAPI_GOOGLE_EMAIL"] = "test@example.com"
    os.environ["TWITTERAPI_SESSION_TOKEN"] = "test-token-123"
    os.environ["TWITTERAPI_REQUEST_TIMEOUT"] = "15"
    
    settings = Settings()
    
    print(f"✅ Settings created successfully")
    print(f"   Google Email: {settings.google_email}")
    print(f"   Session Token: {settings.session_token}")
    print(f"   Base URL: {settings.base_url}")
    print(f"   API Base URL: {settings.api_base_url}")
    print(f"   Request Timeout: {settings.request_timeout}")
    print(f"   Headless: {settings.headless}")
    
    # Test explicit settings
    explicit_settings = Settings(
        google_email="explicit@example.com",
        session_token="explicit-token",
        request_timeout=20
    )
    
    print(f"\n✅ Explicit settings work")
    print(f"   Google Email: {explicit_settings.google_email}")
    print(f"   Session Token: {explicit_settings.session_token}")
    print(f"   Request Timeout: {explicit_settings.request_timeout}")
    
    return settings

def test_metrics():
    """Test Metrics class"""
    print("\n📊 Testing Metrics class...")
    
    # Test basic metrics
    metrics = Metrics(usage=750, limit=1000, provider="twitterapi-json")
    print(f"✅ Basic metrics created")
    print(f"   Usage: {metrics.usage}")
    print(f"   Limit: {metrics.limit}")
    print(f"   Provider: {metrics.provider}")
    
    # Test with extra data
    extra_metrics = Metrics(
        usage=2500,
        limit=5000,
        provider="twitterapi-test",
        extra={
            "api_key": "test-key-123",
            "qps": 10,
            "recharge_credits": 3000,
            "bonus_credits": 2000,
            "api_calls_30day": 1250
        }
    )
    
    print(f"\n✅ Extended metrics created")
    print(f"   Usage: {extra_metrics.usage}")
    print(f"   Limit: {extra_metrics.limit}")
    print(f"   Provider: {extra_metrics.provider}")
    print(f"   Extra data: {extra_metrics.extra}")
    
    # Test edge cases
    zero_limit_metrics = Metrics(usage=100, limit=0, provider="twitterapi-json")
    
    return metrics

def test_json_serialization():
    """Test JSON serialization"""
    print("\n🔄 Testing JSON serialization...")
    
    settings = Settings(
        google_email="json@example.com",
        session_token="json-token"
    )
    
    metrics = Metrics(
        usage=1500,
        limit=2000,
        provider="twitterapi-json",
        extra={"test": "data"}
    )
    
    # Test model_dump_json
    settings_json = settings.model_dump_json(indent=2)
    metrics_json = metrics.model_dump_json(indent=2)
    
    print("✅ JSON serialization successful")
    print(f"Settings JSON length: {len(settings_json)} chars")
    print(f"Metrics JSON length: {len(metrics_json)} chars")
    
    print("\nMetrics JSON:")
    print(metrics_json)

def main():
    """Main test function"""
    print("🧪 Testing TwitterAPI Settings and Metrics")
    print("="*60)
    
    try:
        settings = test_settings()
        metrics = test_metrics()
        test_json_serialization()
        
        print("\n🎉 All TwitterAPI model tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
    
    print("="*60)

if __name__ == "__main__":
    main()
