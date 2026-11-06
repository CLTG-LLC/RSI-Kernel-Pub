import json, sys
print(json.dumps({"prompt": sys.stdin.read().rstrip("\n")}))
