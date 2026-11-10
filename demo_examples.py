"""
Built-in demo examples for the Autonomous Software Debugging Agent.
Each example provides a buggy code snippet/project spec, a test snippet/trigger, and the corresponding error log.
"""

DEMO_EXAMPLES = {
    "Python: ZeroDivisionError": {
        "title": "Calculate Average (Empty List)",
        "language": "python",
        "filename": "demo.py",
        "code": '''def calculate_average(numbers):
    total = sum(numbers)
    count = len(numbers)
    return total / count

print(calculate_average([]))
''',
        "error_log": '''Traceback (most recent call last):
  File "demo.py", line 6, in <module>
    print(calculate_average([]))
  File "demo.py", line 4, in calculate_average
    return total / count
ZeroDivisionError: division by zero''',
        "test_code": '''def test_calculate_average():
    assert calculate_average([10, 20, 30]) == 20.0
    assert calculate_average([]) == 0.0
'''
    },

    "Python: SyntaxError": {
        "title": "Missing Colon in Function Definition",
        "language": "python",
        "filename": "demo.py",
        "code": '''def greet(name)
    print("Hello " + name)
''',
        "error_log": '''  File "demo.py", line 1
    def greet(name)
                   ^
SyntaxError: expected ':' ''',
        "test_code": ""
    },

    "Python: IndentationError": {
        "title": "Unexpected Indentation",
        "language": "python",
        "filename": "demo.py",
        "code": '''def process():
    x = 10
      y = 20
    return x + y
''',
        "error_log": '''  File "demo.py", line 3
    y = 20
    ^
IndentationError: unexpected indent''',
        "test_code": ""
    },

    "Python: NameError": {
        "title": "Undefined Variable",
        "language": "python",
        "filename": "demo.py",
        "code": '''def compute_sum(a, b):
    return a + b + undefined_var

print(compute_sum(5, 10))
''',
        "error_log": '''Traceback (most recent call last):
  File "demo.py", line 4, in <module>
    print(compute_sum(5, 10))
  File "demo.py", line 2, in compute_sum
    return a + b + undefined_var
NameError: name 'undefined_var' is not defined''',
        "test_code": ""
    },

    "Python: TypeError": {
        "title": "String / Int Concatenation",
        "language": "python",
        "filename": "demo.py",
        "code": '''def apply_discount(price, discount):
    return price - (price * (discount / 100))

print(apply_discount(100, "20"))
''',
        "error_log": '''Traceback (most recent call last):
  File "demo.py", line 4, in <module>
    print(apply_discount(100, "20"))
  File "demo.py", line 2, in apply_discount
    return price - (price * (discount / 100))
TypeError: unsupported operand type(s) for /: 'str' and 'int\'''',
        "test_code": ""
    },

    "Python: IndexError": {
        "title": "List Out of Bounds",
        "language": "python",
        "filename": "demo.py",
        "code": '''def get_third_item(items):
    return items[2]

print(get_third_item([10, 20]))
''',
        "error_log": '''Traceback (most recent call last):
  File "demo.py", line 4, in <module>
    print(get_third_item([10, 20]))
  File "demo.py", line 2, in get_third_item
    return items[2]
IndexError: list index out of range''',
        "test_code": ""
    },

    "Python: KeyError": {
        "title": "Missing Key in Dictionary",
        "language": "python",
        "filename": "demo.py",
        "code": '''def get_user_email(user):
    return user["email"]

print(get_user_email({"name": "Alice"}))
''',
        "error_log": '''Traceback (most recent call last):
  File "demo.py", line 4, in <module>
    print(get_user_email({"name": "Alice"}))
  File "demo.py", line 2, in get_user_email
    return user["email"]
KeyError: 'email\'''',
        "test_code": ""
    },

    "Python: AttributeError": {
        "title": "Missing Attribute on Object",
        "language": "python",
        "filename": "demo.py",
        "code": '''text = 12345
print(text.upper())
''',
        "error_log": '''Traceback (most recent call last):
  File "demo.py", line 2, in <module>
    print(text.upper())
AttributeError: 'int' object has no attribute 'upper\'''',
        "test_code": ""
    },

    "Python: ModuleNotFoundError": {
        "title": "Import Nonexistent Module",
        "language": "python",
        "filename": "demo.py",
        "code": '''import non_existent_package_xyz

print("Done")
''',
        "error_log": '''Traceback (most recent call last):
  File "demo.py", line 1, in <module>
    import non_existent_package_xyz
ModuleNotFoundError: No module named 'non_existent_package_xyz\'''',
        "test_code": ""
    },

    "Python: FileNotFoundError": {
        "title": "Open Nonexistent File",
        "language": "python",
        "filename": "demo.py",
        "code": '''with open("non_existent_file.txt", "r") as f:
    content = f.read()
''',
        "error_log": '''Traceback (most recent call last):
  File "demo.py", line 1, in <module>
    with open("non_existent_file.txt", "r") as f:
FileNotFoundError: [Errno 2] No such file or directory: 'non_existent_file.txt\'''',
        "test_code": ""
    },

    "Python: Clean Working Code": {
        "title": "Clean Math Utility",
        "language": "python",
        "filename": "demo.py",
        "code": '''def multiply(a, b):
    return a * b

if __name__ == "__main__":
    result = multiply(4, 5)
    print(f"Result: {result}")
''',
        "error_log": "",
        "test_code": '''def test_multiply():
    assert multiply(4, 5) == 20
'''
    },

    "Logical: Wrong Calculation": {
        "title": "Subtraction Instead of Addition",
        "language": "python",
        "filename": "demo.py",
        "code": '''def add(a, b):
    return a - b
''',
        "error_log": "",
        "test_code": '''def test_add():
    assert add(2, 3) == 5
'''
    },

    "Logical: Off-By-One": {
        "title": "Loop Skips Last Item",
        "language": "python",
        "filename": "demo.py",
        "code": '''def sum_array(arr):
    total = 0
    for i in range(len(arr) - 1):
        total += arr[i]
    return total
''',
        "error_log": "",
        "test_code": '''def test_sum_array():
    assert sum_array([1, 2, 3, 4]) == 10
'''
    },

    "Java: Cannot Find Symbol (Compilation)": {
        "title": "Undefined Symbol in Java",
        "language": "java",
        "filename": "Main.java",
        "code": '''public class Main {
    public static void main(String[] args) {
        System.out.println(unknownVariable);
    }
}
''',
        "error_log": '''Main.java:3: error: cannot find symbol
        System.out.println(unknownVariable);
                           ^
  symbol:   variable unknownVariable
  location: class Main
1 error''',
        "test_code": ""
    },

    "Java: NullPointerException": {
        "title": "Method Call on Null Object",
        "language": "java",
        "filename": "Main.java",
        "code": '''public class Main {
    public static void main(String[] args) {
        String text = null;
        System.out.println(text.length());
    }
}
''',
        "error_log": '''Exception in thread "main" java.lang.NullPointerException: Cannot invoke "String.length()" because "text" is null
	at Main.main(Main.java:4)''',
        "test_code": ""
    },

    "Java: ArithmeticException": {
        "title": "Division by Zero in Java",
        "language": "java",
        "filename": "Main.java",
        "code": '''public class Main {
    public static void main(String[] args) {
        int a = 10;
        int b = 0;
        int result = a / b;
        System.out.println(result);
    }
}
''',
        "error_log": '''Exception in thread "main" java.lang.ArithmeticException: / by zero
	at Main.main(Main.java:5)''',
        "test_code": ""
    },

    "Java: ArrayIndexOutOfBoundsException": {
        "title": "Array Index Out of Range in Java",
        "language": "java",
        "filename": "Main.java",
        "code": '''public class Main {
    public static void main(String[] args) {
        int[] nums = {1, 2, 3};
        System.out.println(nums[5]);
    }
}
''',
        "error_log": '''Exception in thread "main" java.lang.ArrayIndexOutOfBoundsException: Index 5 out of bounds for length 3
	at Main.main(Main.java:4)''',
        "test_code": ""
    },

    "Java: Clean Working Code": {
        "title": "Clean Hello World in Java",
        "language": "java",
        "filename": "Main.java",
        "code": '''public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, Autonomous Debugger!");
    }
}
''',
        "error_log": "",
        "test_code": ""
    }
}

# Project Presets for testing ZIP upload
DEMO_PROJECT_PRESETS = {
    "Python ZIP (ZeroDivisionError)": {
        "language": "python",
        "filename": "python_bug_project.zip",
        "files": {
            "main.py": '''def calculate_average(numbers):
    total = sum(numbers)
    count = len(numbers)
    return total / count
''',
            "test_main.py": '''import pytest
from main import calculate_average

def test_calculate_average_normal():
    assert calculate_average([10, 20, 30]) == 20.0

def test_calculate_average_empty():
    assert calculate_average([]) == 0.0
''',
            "requirements.txt": "pytest>=7.0.0\n"
        }
    },
    "Java Maven ZIP (NullPointerException)": {
        "language": "java",
        "filename": "java_bug_project.zip",
        "files": {
            "pom.xml": '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>java-bug-project</artifactId>
    <version>1.0-SNAPSHOT</version>
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
    </properties>
</project>''',
            "src/main/java/com/example/UserService.java": '''package com.example;

public class UserService {
    public static class User {
        private String name;
        public User(String name) { this.name = name; }
        public String getName() { return name; }
    }

    public String getUserGreeting(User user) {
        return "Hello " + user.getName();
    }
}''',
            "src/test/java/com/example/UserServiceTest.java": '''package com.example;

public class UserServiceTest {
    public static void main(String[] args) {
        UserService service = new UserService();
        System.out.println(service.getUserGreeting(null));
    }
}'''
        }
    }
}

