import asyncio
import logging
import sys

# Configure logging to see details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from market_pulse import MarketPulse

async def test_run():
    print("="*80)
    print("RUNNING MARKET PULSE V2 DIAGNOSTICS")
    print("="*80)
    
    pulse = MarketPulse()
    try:
        # Generate the bulletin
        messages = await pulse.generate_pulse()
        
        print(f"\nSUCCESS! Generated {len(messages)} telegram messages:")
        for idx, msg in enumerate(messages):
            print(f"\n--- MESSAGE {idx+1} ---")
            print(msg)
            print("-" * 50)
    except Exception as e:
        logging.exception(f"Failed to generate pulse: {e}")
    finally:
        await pulse.close()

if __name__ == "__main__":
    asyncio.run(test_run())
