import pytest

from scores import load_scores


def make_csv(tmp_path, content, *, encoding="utf-8"):
    """테스트용 CSV 파일을 만들고 경로를 반환한다."""
    path = tmp_path / "scores.csv"
    path.write_bytes(content.encode(encoding))
    return path


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_load_scores_valid_rows(tmp_path, encoding):
    path = make_csv(
        tmp_path,
        '이름,점수\r\n'
        '  김종익  , 85 \r\n'
        '"이,민수",92\r\n',
        encoding=encoding,
    )

    kept, skipped = load_scores(path)

    # 입력 순서를 유지하고, 앞뒤 공백을 제거하며, 점수를 정수로 반환한다.
    assert kept == [("김종익", 85), ("이,민수", 92)]
    assert skipped == []


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        ("김종익", "열 개수가 2가 아님"),
        ("김종익,80,추가값", "열 개수가 2가 아님"),
        ("   ,80", "이름이 비어 있음"),
        ("김종익,   ", "점수가 비어 있음"),
        (",", "이름이 비어 있음"),
        ("김종익,abc", "점수가 정수가 아님"),
        ("김종익,80.5", "점수가 정수가 아님"),
    ],
    ids=[
        "too-few-columns",
        "too-many-columns",
        "blank-name",
        "blank-score",
        "both-fields-empty",
        "text-score",
        "decimal-score",
    ],
)
def test_load_scores_skips_invalid_rows(tmp_path, row, reason):
    path = make_csv(tmp_path, f"이름,점수\n{row}\n")

    assert load_scores(path) == ([], [(2, row, reason)])


def test_load_scores_score_boundaries(tmp_path):
    path = make_csv(
        tmp_path,
        "이름,점수\n"
        "최솟값미만,-1\n"
        "최솟값,0\n"
        "최댓값,100\n"
        "최댓값초과,101\n",
    )

    kept, skipped = load_scores(path)

    assert kept == [("최솟값", 0), ("최댓값", 100)]
    assert skipped == [
        (2, "최솟값미만,-1", "점수가 0~100 밖"),
        (5, "최댓값초과,101", "점수가 0~100 밖"),
    ]


def test_load_scores_ignores_blank_line_and_continues_after_invalid_row(tmp_path):
    path = make_csv(
        tmp_path,
        "이름,점수\n"        # 1: 헤더
        "김종익,90\n"       # 2: 정상
        "\n"               # 3: 빈 줄 — 기록하지 않음
        '"이,민수",abc\n'   # 4: 잘못된 점수
        "박지수,75\n",      # 5: 정상
    )

    kept, skipped = load_scores(path)

    assert kept == [("김종익", 90), ("박지수", 75)]
    assert skipped == [(4, "이,민수,abc", "점수가 정수가 아님")]


@pytest.mark.parametrize(
    "content",
    ["", "이름,점수\n"],
    ids=["empty-file", "header-only"],
)
def test_load_scores_returns_empty_lists_when_there_are_no_data_rows(
    tmp_path, content
):
    path = make_csv(tmp_path, content)

    assert load_scores(path) == ([], [])


def test_load_scores_raises_if_file_does_not_exist(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_scores(tmp_path / "missing.csv")


def test_load_scores_raises_if_file_is_not_valid_utf8(tmp_path):
    path = tmp_path / "invalid_encoding.csv"
    path.write_bytes(b"name,score\nAlice,\xff\n")

    with pytest.raises(UnicodeDecodeError):
        load_scores(path)