#!/usr/bin/env python3
import json
import sys

def main():
    # Read input from stdin
    input_data = json.loads(sys.stdin.read())
    
    operation = input_data.get("operation", "add")
    a = float(input_data.get("a", 0))
    b = float(input_data.get("b", 0))
    
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            print(json.dumps({"error": "Division by zero"}))
            return
        result = a / b
    else:
        print(json.dumps({"error": f"Unknown operation: {operation}"}))
        return
    
    output = {
        "operation": operation,
        "a": a,
        "b": b,
        "result": result
    }
    
    print(json.dumps(output))

if __name__ == "__main__":
    main()
