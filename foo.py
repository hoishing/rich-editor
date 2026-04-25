from dataclasses import dataclass


@dataclass
class User:
    name: str
    age: int

    def greet(self) -> str:
        return f"Hello, {self.name}! You are {self.age}."


def main() -> None:
    users = [User("Alice", 30), User("Bob", 25)]
    for u in users:
        print(u.greet())


if __name__ == "__main__":
    main()
