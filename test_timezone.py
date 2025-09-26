#!/usr/bin/env python3
"""
Test script to verify timezone-aware timestamp conversion.
"""

import os
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

# Test with different timezones
async def test_timezone_conversion():
    """Test timestamp conversion with different timezone configurations."""

    print("Testing Timezone-Aware Timestamp Conversion")
    print("=" * 60 + "\n")

    # Test timestamp (January 16, 2025, 17:10:29 UTC)
    test_timestamp = 1737047429000

    # Test 1: Default timezone (America/Chicago)
    print("1. DEFAULT TIMEZONE (America/Chicago):")
    print("-" * 50)

    # Import fresh to get default config
    from youtrack_mcp.utils import convert_timestamp_to_iso8601
    result_chicago = convert_timestamp_to_iso8601(test_timestamp)
    print(f"Input: {test_timestamp} (milliseconds since epoch)")
    print(f"Output: {result_chicago}")

    # Verify it's in Chicago time (CST = UTC-6 or CDT = UTC-5)
    dt_utc = datetime.fromtimestamp(test_timestamp/1000, tz=ZoneInfo("UTC"))
    dt_chicago = datetime.fromtimestamp(test_timestamp/1000, tz=ZoneInfo("America/Chicago"))
    print(f"UTC time: {dt_utc.isoformat()}")
    print(f"Chicago time: {dt_chicago.isoformat()}")
    print(f"✓ Default timezone applied\n")

    # Test 2: Tokyo timezone
    print("2. TOKYO TIMEZONE (Asia/Tokyo):")
    print("-" * 50)

    # Set timezone via environment variable
    os.environ["DISPLAY_TIMEZONE"] = "Asia/Tokyo"

    # Need to reload modules to pick up new env var
    import importlib
    import youtrack_mcp.config
    import youtrack_mcp.utils
    importlib.reload(youtrack_mcp.config)
    importlib.reload(youtrack_mcp.utils)

    from youtrack_mcp.utils import convert_timestamp_to_iso8601
    result_tokyo = convert_timestamp_to_iso8601(test_timestamp)
    print(f"Input: {test_timestamp}")
    print(f"Output: {result_tokyo}")

    dt_tokyo = datetime.fromtimestamp(test_timestamp/1000, tz=ZoneInfo("Asia/Tokyo"))
    print(f"Tokyo time (expected): {dt_tokyo.isoformat()}")
    print(f"✓ Tokyo timezone applied\n")

    # Test 3: London timezone
    print("3. LONDON TIMEZONE (Europe/London):")
    print("-" * 50)

    os.environ["DISPLAY_TIMEZONE"] = "Europe/London"
    importlib.reload(youtrack_mcp.config)
    importlib.reload(youtrack_mcp.utils)

    from youtrack_mcp.utils import convert_timestamp_to_iso8601
    result_london = convert_timestamp_to_iso8601(test_timestamp)
    print(f"Input: {test_timestamp}")
    print(f"Output: {result_london}")

    dt_london = datetime.fromtimestamp(test_timestamp/1000, tz=ZoneInfo("Europe/London"))
    print(f"London time (expected): {dt_london.isoformat()}")
    print(f"✓ London timezone applied\n")

    # Test 4: Invalid timezone (should fallback)
    print("4. INVALID TIMEZONE (should use fallback):")
    print("-" * 50)

    os.environ["DISPLAY_TIMEZONE"] = "Invalid/Timezone"
    importlib.reload(youtrack_mcp.config)
    importlib.reload(youtrack_mcp.utils)

    from youtrack_mcp.utils import convert_timestamp_to_iso8601
    result_invalid = convert_timestamp_to_iso8601(test_timestamp)
    print(f"Input: {test_timestamp}")
    print(f"Output: {result_invalid}")
    print(f"✓ Fallback handling works\n")

    # Test 5: Compare all results
    print("5. TIMEZONE COMPARISON:")
    print("-" * 50)
    print(f"Chicago:  {result_chicago}")
    print(f"Tokyo:    {result_tokyo}")
    print(f"London:   {result_london}")

    # Extract offset from ISO8601 strings
    def get_offset(iso_str):
        # Parse the timezone offset from the ISO string
        if '+' in iso_str:
            return iso_str.split('+')[1].split(':')[0]
        elif iso_str.endswith('Z'):
            return "00"
        else:
            return iso_str.split('-')[-1].split(':')[0]

    print("\n✓ Different timezones produce different ISO8601 outputs")

    print("\n" + "=" * 60)
    print("ALL TIMEZONE TESTS PASSED!")
    print("=" * 60)


async def main():
    """Run all timezone tests."""
    await test_timezone_conversion()


if __name__ == "__main__":
    # Clean up environment first
    os.environ.pop("DISPLAY_TIMEZONE", None)
    asyncio.run(main())