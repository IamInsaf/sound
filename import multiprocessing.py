import multiprocessing
import time

def stress():
    x = 1
    while True:
        x = (x * 3.14159265359) % 1000000

if __name__ == "__main__":
    cores = multiprocessing.cpu_count()

    print(f"CPU cores detected: {cores}")
    print("Starting CPU stress...")
    print("Press Ctrl+C to stop.")

    workers = []

    try:
        for _ in range(cores):
            p = multiprocessing.Process(target=stress)
            p.start()
            workers.append(p)

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping...")

        for p in workers:
            p.terminate()

        for p in workers:
            p.join()

        print("Done.")