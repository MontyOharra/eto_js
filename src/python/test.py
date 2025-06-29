import sys

def test(switchCase):
    match switchCase:
        case "test1":
            return "Hello, World! 1"
        case "test2":
            return "Hello, World! 2"
        case _:
            return "Hello, World! 0"
  
if __name__ == "__main__":
    switch = sys.argv[1] if len(sys.argv) > 1 else "test"
    print(test(switch))