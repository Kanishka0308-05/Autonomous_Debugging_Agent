def apply_discount(price, discount_percent):
    return price - (price * (discount_percent / 100))

if __name__ == "__main__":
    print(apply_discount(100, "20"))
