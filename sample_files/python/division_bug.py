def calculate_average(numbers):
    total = sum(numbers)
    count = len(numbers)
    return total / count

if __name__ == "__main__":
    print(calculate_average([]))
