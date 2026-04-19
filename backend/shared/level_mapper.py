class LevelMapper:
    # Thang điểm từ 1-5
    LEVEL_MAP = {
        "beginner": 1, "basic": 1, "intern": 1, "novice": 1,
        "junior": 2, "low": 2,
        "middle": 3, "intermediate": 3, "mid": 3, "mid-level": 3,
        "senior": 4, "advanced": 4, "high": 4,
        "expert": 5, "lead": 5, "specialist": 5
    }

    REVERSE_MAP = {
        1: "Basic/Beginner",
        2: "Junior",
        3: "Mid-level",
        4: "Senior",
        5: "Expert"
    }

    @classmethod
    def to_score(cls, level_str: str) -> int:
        if not level_str: return 1 # Mặc định là Beginner nếu không ghi
        return cls.LEVEL_MAP.get(level_str.lower().strip(), 1)

    @classmethod
    def to_label(cls, score: int) -> str:
        return cls.REVERSE_MAP.get(score, "Unknown")

    @classmethod
    def calculate_gap(cls, user_level_str: str, required_level_str: str) -> int:
        u_score = cls.to_score(user_level_str)
        r_score = cls.to_score(required_level_str)
        return r_score - u_score
