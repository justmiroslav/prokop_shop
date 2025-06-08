import os

class AuthManager:
    def __init__(self):
        self.authorized_file = "data/authorized_users.txt"
        self.banned_file = "data/banned_users.txt"
        self.ensure_data_directory(self.authorized_file)
        self.ensure_data_directory(self.banned_file)
        self.authorized_users = self.load_data(self.authorized_file)
        self.banned_users = self.load_data(self.banned_file)
        self.failed_attempts = {}
        self.MAX_FAILED_ATTEMPTS = 5

    @staticmethod
    def load_data(file_path: str) -> set[int]:
        if not os.path.exists(file_path):
            return set()
        with open(file_path, "r") as file:
            return {int(line.strip()) for line in file}

    @staticmethod
    def save_data(data: set[int], file_path: str):
        with open(file_path, "w") as file:
            file.write("\n".join(str(user_id) for user_id in data))

    @staticmethod
    def ensure_data_directory(file_path: str) -> None:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    def is_user_authorized(self, user_id: int) -> bool:
        return user_id in self.load_data(self.authorized_file)

    def is_user_banned(self, user_id: int) -> bool:
        return user_id in self.load_data(self.banned_file)

    def authorize_user(self, user_id: int):
        self.authorized_users.add(user_id)
        self.failed_attempts.pop(user_id, None)
        self.save_data(self.authorized_users, self.authorized_file)

    def ban_user(self, user_id: int):
        self.banned_users.add(user_id)
        self.failed_attempts.pop(user_id, None)
        self.save_data(self.banned_users, self.banned_file)

    def add_failed_attempt(self, user_id: int) -> int:
        self.failed_attempts[user_id] = self.failed_attempts.get(user_id, 0) + 1
        return self.MAX_FAILED_ATTEMPTS - self.failed_attempts[user_id]

auth_manager = AuthManager()
