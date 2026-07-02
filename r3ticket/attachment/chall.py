import secrets
import signal
import time
import gmpy2

READY_DELAY = 10
ANSWER_TIMEOUT = 3

def timeout_handler(signum, frame):
    print("Too slow...")
    raise SystemExit


def timed_input(prompt, timeout):
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        return input(prompt)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


signal.signal(signal.SIGALRM, timeout_handler)

nums = [gmpy2.mpz(secrets.randbits(16)) for _ in range(128)]

def get_num(nums, index):
    if index > len(nums) - 1:
        return 0
    result = 0
    for i in range(len(nums)):
        part = 1
        for j in range(len(nums)):
            if j == i:
                continue
            part *= (index - j) // (i - j)
        result += part * nums[i]
    return result

index = int(input("Which number you want to know: "))
print("Here is what you want:", get_num(nums, index))
print("Get ready...")
time.sleep(READY_DELAY)
print("Lets play!")

for round in range(16):
    print(f"{round + 1}/16")
    x = secrets.randbits(24)
    h = sum([num**x for num in nums])
    print("challenge =", str(h)[:64])

    check = int(timed_input("x = ", ANSWER_TIMEOUT))
    if check != x:
        print("You lose...")
        exit()

flag = open("flag.txt", "r").read()
print("You won! Here is your real ticket:", flag)