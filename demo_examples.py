"""
Built-in demo examples for the Autonomous Software Debugging Agent.
Each example provides a buggy code snippet/project spec, a test snippet/trigger, and the corresponding error log.
"""

DEMO_EXAMPLES = {
    "ZeroDivisionError (Empty List)": {
        "title": "Calculate Average (Empty List)",
        "code": '''def calculate_average(numbers):
    total = sum(numbers)
    count = len(numbers)
    return total / count

# Execution that triggers bug:
print(calculate_average([]))
''',
        "error_log": '''Traceback (most recent call last):
  File "main.py", line 6, in <module>
    print(calculate_average([]))
  File "main.py", line 4, in calculate_average
    return total / count
ZeroDivisionError: division by zero''',
        "test_code": '''def test_calculate_average():
    assert calculate_average([10, 20, 30]) == 20.0
    assert calculate_average([5]) == 5.0
    assert calculate_average([]) == 0.0
'''
    },

    "IndexError (Out of Bounds)": {
        "title": "Access Array Element (Out of Bounds)",
        "code": '''def get_third_element(items):
    return items[2]

# Execution that triggers bug:
print(get_third_element([10, 20]))
''',
        "error_log": '''Traceback (most recent call last):
  File "main.py", line 5, in <module>
    print(get_third_element([10, 20]))
  File "main.py", line 2, in get_third_element
    return items[2]
IndexError: list index out of range''',
        "test_code": '''def test_get_third_element():
    assert get_third_element([10, 20, 30]) == 30
    assert get_third_element([10, 20]) is None
'''
    },

    "TypeError (String/Int Concatenation)": {
        "title": "Calculate Discount (String Input)",
        "code": '''def apply_discount(price, discount_percent):
    discount_amount = price * (discount_percent / 100)
    return price - discount_amount

# Execution that triggers bug:
print(apply_discount(100, "20"))
''',
        "error_log": '''Traceback (most recent call last):
  File "main.py", line 6, in <module>
    print(apply_discount(100, "20"))
  File "main.py", line 2, in apply_discount
    discount_amount = price * (discount_percent / 100)
TypeError: unsupported operand type(s) for /: 'str' and 'int\'''',
        "test_code": '''def test_apply_discount():
    assert apply_discount(100, 20) == 80.0
    assert apply_discount(100, "20") == 80.0
'''
    },

    "KeyError (Missing Dictionary Key)": {
        "title": "Extract User Email (Missing Key)",
        "code": '''def get_user_email(user_profile):
    return user_profile["email"]

# Execution that triggers bug:
user = {"name": "Alice", "id": 101}
print(get_user_email(user))
''',
        "error_log": '''Traceback (most recent call last):
  File "main.py", line 6, in <module>
    print(get_user_email(user))
  File "main.py", line 2, in get_user_email
    return user_profile["email"]
KeyError: 'email\'''',
        "test_code": '''def test_get_user_email():
    assert get_user_email({"name": "Alice", "email": "alice@example.com"}) == "alice@example.com"
    assert get_user_email({"name": "Bob"}) is None or get_user_email({"name": "Bob"}) == ""
'''
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
