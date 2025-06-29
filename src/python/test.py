import sys

def test(switchCase):
    match switchCase:
        case "test":
            return "Hello, World!"
        case "test2":
            return "Hello, World! 2"
        case _:
            return "Hello, World! 3"
  
if __name__ == "__main__":
    switch = sys.argv[1] if len(sys.argv) > 1 else "test"
    print(test(switch))