"""
Error patterns, categories, and taxonomy rules for the Error Classification Engine.
Supports Python and Java compiler, runtime, static analysis, and logical errors.
"""

# Major Categories Taxonomy
CATEGORY_SYNTAX_ERROR = "SYNTAX_ERROR"
CATEGORY_COMPILE_ERROR = "COMPILE_ERROR"
CATEGORY_TYPE_ERROR = "TYPE_ERROR"
CATEGORY_NAME_ERROR = "NAME_ERROR"
CATEGORY_RUNTIME_ERROR = "RUNTIME_ERROR"
CATEGORY_IMPORT_ERROR = "IMPORT_ERROR"
CATEGORY_FILE_IO_ERROR = "FILE_IO_ERROR"
CATEGORY_DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
CATEGORY_TEST_FAILURE = "TEST_FAILURE"
CATEGORY_LOGICAL_ERROR = "LOGICAL_ERROR"
CATEGORY_OTHER_RUNTIME = "OTHER_RUNTIME_ERROR"
CATEGORY_OTHER_COMPILE = "OTHER_COMPILE_ERROR"
CATEGORY_UNKNOWN = "UNKNOWN_ERROR"

# Sources
SOURCE_STATIC_ANALYSIS = "static_analysis"
SOURCE_COMPILER = "compiler"
SOURCE_RUNTIME = "runtime"
SOURCE_TEST = "test"
SOURCE_DEPENDENCY = "dependency"
SOURCE_UNKNOWN = "unknown"

# Severities
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"
SEVERITY_NONE = "NONE"

# Confidences
CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"

# Python Known Error Map
PYTHON_ERROR_MAP = {
    "SyntaxError": {
        "category": CATEGORY_SYNTAX_ERROR,
        "subtype": "INVALID_SYNTAX",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_STATIC_ANALYSIS
    },
    "IndentationError": {
        "category": CATEGORY_SYNTAX_ERROR,
        "subtype": "INDENTATION_ERROR",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_STATIC_ANALYSIS
    },
    "TabError": {
        "category": CATEGORY_SYNTAX_ERROR,
        "subtype": "TAB_SPACE_MISMATCH",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_STATIC_ANALYSIS
    },
    "NameError": {
        "category": CATEGORY_NAME_ERROR,
        "subtype": "UNDEFINED_VARIABLE",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "UnboundLocalError": {
        "category": CATEGORY_NAME_ERROR,
        "subtype": "UNBOUND_LOCAL_VARIABLE",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "TypeError": {
        "category": CATEGORY_TYPE_ERROR,
        "subtype": "INCOMPATIBLE_TYPES",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "ValueError": {
        "category": CATEGORY_TYPE_ERROR,
        "subtype": "INVALID_VALUE",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "IndexError": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "INDEX_OUT_OF_BOUNDS",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "KeyError": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "MISSING_KEY",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "AttributeError": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "MISSING_ATTRIBUTE",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "ZeroDivisionError": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "DIVISION_BY_ZERO",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "ImportError": {
        "category": CATEGORY_IMPORT_ERROR,
        "subtype": "IMPORT_FAILED",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_DEPENDENCY
    },
    "ModuleNotFoundError": {
        "category": CATEGORY_IMPORT_ERROR,
        "subtype": "MODULE_NOT_FOUND",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_DEPENDENCY
    },
    "FileNotFoundError": {
        "category": CATEGORY_FILE_IO_ERROR,
        "subtype": "FILE_NOT_FOUND",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "PermissionError": {
        "category": CATEGORY_FILE_IO_ERROR,
        "subtype": "PERMISSION_DENIED",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "RecursionError": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "MAX_RECURSION_EXCEEDED",
        "severity": SEVERITY_CRITICAL,
        "source": SOURCE_RUNTIME
    },
    "OverflowError": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "NUMERIC_OVERFLOW",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "MemoryError": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "OUT_OF_MEMORY",
        "severity": SEVERITY_CRITICAL,
        "source": SOURCE_RUNTIME
    },
    "RuntimeError": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "GENERIC_RUNTIME_FAILURE",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "AssertionError": {
        "category": CATEGORY_TEST_FAILURE,
        "subtype": "ASSERTION_FAILED",
        "severity": SEVERITY_MEDIUM,
        "source": SOURCE_TEST
    }
}

# Java Known Exception & Compiler Pattern Map
JAVA_RUNTIME_MAP = {
    "NullPointerException": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "NULL_DEREFERENCE",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "ArithmeticException": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "DIVISION_BY_ZERO",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "ArrayIndexOutOfBoundsException": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "INDEX_OUT_OF_BOUNDS",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "IndexOutOfBoundsException": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "INDEX_OUT_OF_BOUNDS",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "NumberFormatException": {
        "category": CATEGORY_TYPE_ERROR,
        "subtype": "NUMBER_PARSING_FAILURE",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "ClassCastException": {
        "category": CATEGORY_TYPE_ERROR,
        "subtype": "INVALID_CAST",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "IllegalArgumentException": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "INVALID_ARGUMENT",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "IllegalStateException": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "INVALID_STATE",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "ConcurrentModificationException": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "CONCURRENT_MODIFICATION",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "StackOverflowError": {
        "category": CATEGORY_RUNTIME_ERROR,
        "subtype": "RECURSION_LIMIT",
        "severity": SEVERITY_CRITICAL,
        "source": SOURCE_RUNTIME
    },
    "AssertionError": {
        "category": CATEGORY_TEST_FAILURE,
        "subtype": "ASSERTION_FAILED",
        "severity": SEVERITY_MEDIUM,
        "source": SOURCE_TEST
    },
    "FileNotFoundException": {
        "category": CATEGORY_FILE_IO_ERROR,
        "subtype": "FILE_NOT_FOUND",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    },
    "IOException": {
        "category": CATEGORY_FILE_IO_ERROR,
        "subtype": "IO_FAILURE",
        "severity": SEVERITY_HIGH,
        "source": SOURCE_RUNTIME
    }
}

JAVA_COMPILER_PATTERNS = [
    (r"';' expected", CATEGORY_COMPILE_ERROR, "SYNTAX_PUNCTUATION", SEVERITY_HIGH),
    (r"cannot find symbol", CATEGORY_COMPILE_ERROR, "UNRESOLVED_SYMBOL", SEVERITY_HIGH),
    (r"incompatible types", CATEGORY_COMPILE_ERROR, "TYPE_MISMATCH", SEVERITY_HIGH),
    (r"missing return statement", CATEGORY_COMPILE_ERROR, "MISSING_RETURN", SEVERITY_HIGH),
    (r"method .* cannot be applied to", CATEGORY_COMPILE_ERROR, "INVALID_METHOD_SIGNATURE", SEVERITY_HIGH),
    (r"class, interface, enum, or record expected", CATEGORY_COMPILE_ERROR, "INVALID_STRUCTURE", SEVERITY_HIGH),
    (r"reached end of file while parsing", CATEGORY_COMPILE_ERROR, "UNCLOSED_BLOCK", SEVERITY_HIGH)
]
