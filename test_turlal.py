import unittest

from turlal import TurlalSyntaxError, transpile


class TurlalTests(unittest.TestCase):
    def test_core_syntax_transpiles(self):
        source = """터랄 더하기(왼쪽, 오른쪽) 은 내가 만든 말이야!!
    터바 왼쪽 + 오른쪽
값 나이는 더하기(2, 5)
야 값 > 5 아니잖아!!
    마그마 값 올리자
아니 야 값 == 5 아니잖아!!
    마그마 0 올리자
아니!!
    마그마 2 올리자
등신 애쓴다 ㅋㅋ
"""
        result = transpile(source)
        self.assertIn("def 더하기(왼쪽, 오른쪽):", result)
        self.assertIn("elif 값 == 5:", result)
        self.assertIn("print(값)", result)

    def test_raw_python_is_preserved(self):
        source = """아싸리
x = 17
print(x)
는 내가만든 말이 아니야
등신 애쓴다 ㅋㅋ
"""
        self.assertIn("x = 17", transpile(source))

    def test_forbidden_number_is_rejected_outside_raw_block(self):
        source = """값 나이는 7
등신 애쓴다 ㅋㅋ
"""
        with self.assertRaises(TurlalSyntaxError):
            transpile(source)

    def test_terminator_is_required(self):
        with self.assertRaises(TurlalSyntaxError):
            transpile("마그마 2 올리자\n")


if __name__ == "__main__":
    unittest.main()
