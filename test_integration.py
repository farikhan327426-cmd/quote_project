import sys
import os

print("--- Integration Test Starting ---")

try:
    print("1. Attempting to import shared_core...")
    from shared_core.logger.logging import log
    from shared_core.exception.exceptionhandling import CustomException
    print("   [SUCCESS] Shared Core imported.")

    print("2. Testing Logger...")
    log.info("Test Log Message from Integration Script")
    print("   [SUCCESS] Logger functioned correctly.")

    print("3. Testing Exception Class...")
    try:
        raise ValueError("Simulated Error")
    except ValueError as e:
        ce = CustomException(e, sys)
        print(f"   [SUCCESS] CustomException created: {ce}")

    print("\nXXX ALL SYSTEMS GO - WORKSPACE INTEGRATION VERIFIED XXX")

except ImportError as e:
    print(f"\n[FAILURE] Import Failed: {e}")
    print("Sys Path:", sys.path)
    sys.exit(1)
except Exception as e:
    print(f"\n[FAILURE] Unexpected Error: {e}")
    sys.exit(1)
