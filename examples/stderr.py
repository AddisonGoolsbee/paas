import time
import sys

def main():
    print("Starting script...")  # stdout
    time.sleep(1)

    # Simulate a mix of stdout and stderr output
    for i in range(5):
        print(f"Iteration {i + 1}: All systems nominal.", flush=True)  # stdout
        time.sleep(0.5)
        print(f"Warning: Minor issue in iteration {i + 1}.", file=sys.stderr, flush=True)  # stderr
        time.sleep(0.5)

    print("Performing a complex calculation...", flush=True)
    time.sleep(2)

    # Simulate an error
    print("Error: Unable to complete calculation.", file=sys.stderr, flush=True)
    time.sleep(1)

    # Final output
    print("Script execution complete.", flush=True)


if __name__ == "__main__":
    main()
