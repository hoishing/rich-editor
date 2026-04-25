interface User {
  readonly id: number;
  name: string;
  email?: string;
}

type Role = "admin" | "editor" | "viewer";

abstract class Repository<T extends { id: number }> {
  protected items: Map<number, T> = new Map();

  abstract validate(item: T): boolean;

  add(item: T): void {
    if (!this.validate(item)) throw new Error("invalid");
    this.items.set(item.id, item);
  }

  get(id: number): T | undefined {
    return this.items.get(id);
  }
}

class UserRepo extends Repository<User> {
  validate(u: User): boolean {
    return u.name.length > 0;
  }
}

const repo = new UserRepo();
repo.add({ id: 1, name: "Alice", email: "a@x.com" });
console.log(repo.get(1));
