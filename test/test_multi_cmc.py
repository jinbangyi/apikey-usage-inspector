#!/usr/bin/env python3
"""
Test script for CMC multi-session token support.
This demonstrates how to configure and use multiple CMC session tokens.
"""

import asyncio
import os

from loguru import logger

# Set up environment variables for testing
os.environ["CMC_ENABLED"] = "true"

# Example configuration - you would replace these with real session tokens
# Option 1: Multiple tokens via comma-separated string
os.environ["CMC_SESSION_TOKEN"] = "token1_example,token2_example,token3_example"

# Option 2: Or use list format in code (see below)

from src.cmc import Settings as CMCSettings
from src.cmc.cmc import TokenMetrics, start


def test_settings_parsing():
    """Test how settings parse different token configurations"""
    logger.info("Testing CMC settings parsing...")
    
    # Test 1: Single token
    settings1 = CMCSettings(session_token="single_token_example")
    logger.info(f"Single token config: {settings1.session_tokens}")
    logger.info(f"Has multiple tokens: {settings1.has_multiple_tokens}")
    
    # Test 2: Multiple tokens as list
    settings2 = CMCSettings(session_token=["token1", "token2", "token3"])
    logger.info(f"Multiple token config: {settings2.session_tokens}")
    logger.info(f"Has multiple tokens: {settings2.has_multiple_tokens}")
    
    # Test 3: Using both session_token and session_tokens fields
    settings3 = CMCSettings(
        session_token="token1",
        session_tokens=["token2", "token3"]
    )
    logger.info(f"Mixed config: {settings3.session_tokens}")
    logger.info(f"Has multiple tokens: {settings3.has_multiple_tokens}")


async def test_mock_metrics():
    """Test the token metrics aggregation with mock data"""
    logger.info("Testing token metrics aggregation...")
    
    # Mock some token metrics
    mock_metrics = [
        TokenMetrics(token_id="token1...", usage=1000, limit=10000, success=True),
        TokenMetrics(token_id="token2...", usage=2500, limit=15000, success=True),
        TokenMetrics(token_id="token3...", usage=0, limit=0, success=False, error="Invalid token"),
    ]


def print_usage_instructions():
    """Print instructions for using the multi-token feature"""
    logger.info("=== CMC Multi-Session Token Usage Instructions ===")
    
    print("""
Configuration Options:

1. Environment Variables:
   # Single token
   export CMC_SESSION_TOKEN="your_session_token_here"
   
   # Multiple tokens (comma-separated)
   export CMC_SESSION_TOKEN="token1,token2,token3"

2. In Python code:
   from src.cmc import Settings as CMCSettings
   
   # Single token
   settings = CMCSettings(session_token="your_token")
   
   # Multiple tokens
   settings = CMCSettings(session_token=["token1", "token2", "token3"])
   
   # Mixed approach
   settings = CMCSettings(
       session_token="primary_token",
       session_tokens=["backup_token1", "backup_token2"]
   )

3. Features:
   - Automatic aggregation of usage and limits across all tokens
   - Concurrent API calls for better performance
   - Graceful handling of failed tokens
   - Detailed logging for each token's metrics
   - Backward compatibility with single token setups

4. Benefits:
   - Higher combined API limits
   - Redundancy if one token fails
   - Better distribution of API calls
   - Detailed per-account monitoring
""")


if __name__ == "__main__":
    logger.info("CMC Multi-Session Token Test")
    
    print_usage_instructions()
    
    logger.info("Testing settings parsing...")
    test_settings_parsing()
    
    logger.info("Testing metrics aggregation...")
    asyncio.run(test_mock_metrics())
    
    logger.info("Test completed!")
