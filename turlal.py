#!/usr/bin/env python3
"""터랄(turlal) 소스를 파이썬으로 변환하고 실행하는 작은 인터프리터."""

from __future__ import annotations

import argparse
import io
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path


TERMINATOR = "등신 애쓴다 ㅋㅋ"
RAW_START = "아싸리"
RAW_END = "는 내가 만든 말이 아니야"
IDENTIFIER = r"[^\W\d]\w*"


class TurlalSyntaxError(Exception):
    """사용자가 고칠 수 있는 터랄 문법 오류."""

    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"{line}번째 줄: {message}")
        self.line = line


@dataclass(frozen=True)
class GeneratedLine:
    source_line: int
    text: str


def _check_number_literals(code: str, line_number: int) -> None:
    """문자열은 제외하고 숫자 리터럴에 0, 2, 5 외 숫자가 없는지 검사한다."""
    try:
        tokens = tokenize.generate_tokens(io.StringIO(code).readline)
        for token in tokens:
            if token.type == tokenize.NUMBER and any(ch not in "025" for ch in token.string):
                raise TurlalSyntaxError(
                    line_number,
                    f"숫자 리터럴 '{token.string}'에는 0, 2, 5만 사용할 수 있습니다.",
                )
    except tokenize.TokenError as error:
        raise TurlalSyntaxError(line_number, f"표현식을 해석할 수 없습니다: {error.args[0]}") from error


def _split_indent(line: str) -> tuple[str, str]:
    match = re.match(r"^(\s*)(.*)$", line)
    assert match is not None
    return match.group(1), match.group(2)


def transpile(source: str) -> str:
    """터랄 소스를 동등한 파이썬 소스로 변환한다."""
    lines = source.splitlines()
    last_code_line = next((index for index in range(len(lines) - 1, -1, -1) if lines[index].strip()), None)
    if last_code_line is None or lines[last_code_line].strip() != TERMINATOR:
        raise TurlalSyntaxError(len(lines) or 1, f"스크립트 마지막 줄은 '{TERMINATOR}'이어야 합니다.")

    generated: list[GeneratedLine] = []
    raw_mode = False
    raw_start_line = 0

    for index, original in enumerate(lines[:last_code_line], start=1):
        indent, stripped = _split_indent(original)

        if raw_mode:
            if stripped == RAW_END:
                raw_mode = False
            else:
                generated.append(GeneratedLine(index, original))
            continue

        if stripped == RAW_START:
            raw_mode = True
            raw_start_line = index
            continue

        if stripped == RAW_END:
            raise TurlalSyntaxError(index, f"'{RAW_END}' 앞에는 '{RAW_START}'가 필요합니다.")

        # 빈 줄과 주석은 그대로 둔다.
        if not stripped or stripped.startswith("#"):
            generated.append(GeneratedLine(index, original))
            continue

        translated: str | None = None

        match = re.fullmatch(rf"터하\s+({IDENTIFIER}(?:\.{IDENTIFIER})*)(?:\s+틀하\s+({IDENTIFIER}))?", stripped)
        if match:
            module, alias = match.groups()
            translated = f"import {module}" + (f" as {alias}" if alias else "")

        match = re.fullmatch(rf"스하\s+({IDENTIFIER}(?:\.{IDENTIFIER})*)\s+터하\s+\*", stripped)
        if match:
            translated = f"from {match.group(1)} import *"

        match = re.fullmatch(rf"터랄\s+({IDENTIFIER}\s*\(.*\))\s+은\s+내가\s+만든\s+말이야!!", stripped)
        if match:
            translated = f"def {match.group(1)}:"

        match = re.fullmatch(r"터바(?:\s+(.+))?", stripped)
        if match:
            value = match.group(1)
            translated = "return" if value is None else f"return {value}"

        match = re.fullmatch(r"야\s+(.+?)\s+아니잖아!!", stripped)
        if match:
            translated = f"if {match.group(1)}:"

        match = re.fullmatch(r"아니\s+야\s+(.+?)\s+아니잖아!!", stripped)
        if match:
            translated = f"elif {match.group(1)}:"

        if stripped == "아니!!":
            translated = "else:"

        match = re.fullmatch(r"정병\s+(.+?)\s+동안!!", stripped)
        if match:
            translated = f"while {match.group(1)}:"

        match = re.fullmatch(r"마그마\s+(.+?)\s+올리자", stripped)
        if match:
            translated = f"print({match.group(1)})"

        match = re.fullmatch(rf"({IDENTIFIER})\s+나이는\s+(.+)", stripped)
        if match:
            translated = f"{match.group(1)} = {match.group(2)}"

        if translated is None:
            raise TurlalSyntaxError(index, "알 수 없는 터랄 문장입니다. 파이썬은 '아싸리' 블록 안에서 사용하세요.")

        _check_number_literals(translated, index)
        generated.append(GeneratedLine(index, indent + translated))

    if raw_mode:
        raise TurlalSyntaxError(raw_start_line, f"'{RAW_START}' 블록이 '{RAW_END}'로 닫히지 않았습니다.")

    python_source = "\n".join(line.text for line in generated) + "\n"
    try:
        compile(python_source, "<turlal>", "exec")
    except SyntaxError as error:
        source_line = generated[error.lineno - 1].source_line if error.lineno and error.lineno <= len(generated) else 1
        raise TurlalSyntaxError(source_line, f"변환된 파이썬 문법 오류: {error.msg}") from error

    return python_source


def _read_and_transpile(path: Path) -> str:
    try:
        return transpile(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(f"파일을 읽을 수 없습니다: {path}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description="터랄 소스를 파이썬으로 변환하거나 실행합니다.")
    commands = parser.add_subparsers(dest="command", required=True)

    run_parser = commands.add_parser("run", help="터랄 파일을 실행합니다.")
    run_parser.add_argument("source", type=Path)

    transpile_parser = commands.add_parser("transpile", help="터랄 파일을 파이썬으로 변환합니다.")
    transpile_parser.add_argument("source", type=Path)
    transpile_parser.add_argument("-o", "--output", type=Path, help="저장할 .py 경로 (생략하면 화면에 출력)")

    args = parser.parse_args()
    try:
        python_source = _read_and_transpile(args.source)
        if args.command == "transpile":
            if args.output:
                args.output.write_text(python_source, encoding="utf-8")
            else:
                print(python_source, end="")
        else:
            namespace = {"__name__": "__main__", "__file__": str(args.source.resolve())}
            exec(compile(python_source, str(args.source), "exec"), namespace)
    except (TurlalSyntaxError, RuntimeError) as error:
        print(f"터랄 오류: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
