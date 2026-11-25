import pytest

from scores import load_scores


def write_csv(tmp_path, content):
    path = tmp_path / "scores.csv"
    path.write_text(content, encoding="utf-8")
    return path


def assert_skipped_rows(skipped, expected_lines):
    """제외된 줄 번호와 각 기록에 이유가 있는지 검증한다."""
    assert [line_no for line_no, _, _ in skipped] == expected_lines
    for _, _, reason in skipped:
        assert isinstance(reason, str)
        assert reason.strip()


def test_valid_rows_preserve_order_and_original_file(tmp_path):
    path = write_csv(
        tmp_path,
        'name,score\n'
        'Zoe,72\n'
        '"Kim, Jongik",95\n'
        'Amy,80\n',
    )
    original = path.read_bytes()

    kept, skipped = load_scores(path)

    # 이름순·점수순으로 정렬하지 않고 파일에 나온 순서를 유지한다.
    assert kept == [("Zoe", 72), ("Kim, Jongik", 95), ("Amy", 80)]
    assert skipped == []
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    ("score_text", "expected_score"),
    [
        ("-1", None),
        ("0", 0),
        ("100", 100),
        ("101", None),
    ],
    ids=["below-minimum", "minimum", "maximum", "above-maximum"],
)
def test_score_boundaries(tmp_path, score_text, expected_score):
    path = write_csv(tmp_path, f"name,score\nKim,{score_text}\n")

    kept, skipped = load_scores(path)

    if expected_score is None:
        assert kept == []
        assert_skipped_rows(skipped, [2])
    else:
        assert kept == [("Kim", expected_score)]
        assert skipped == []


@pytest.mark.parametrize(
    "invalid_row",
    ["Kim", "Kim,80,extra", ",80", "Kim,", "Kim,not-a-number"],
    ids=["one-column", "three-columns", "missing-name", "missing-score", "invalid-score"],
)
def test_invalid_row_is_recorded_and_later_valid_row_is_kept(tmp_path, invalid_row):
    path = write_csv(
        tmp_path,
        f"name,score\n{invalid_row}\nLee,82\n",
    )

    kept, skipped = load_scores(path)

    # 잘못된 점수를 0이나 평균으로 대체하지 않고, 다음 행도 계속 읽는다.
    assert kept == [("Lee", 82)]
    assert_skipped_rows(skipped, [2])


def test_duplicate_name_keeps_first_valid_score(tmp_path):
    path = write_csv(
        tmp_path,
        "name,score\n"
        "Kim,invalid\n"  # 2: 유효하지 않으므로 이름을 선점하지 않음
        "Kim,75\n"       # 3: Kim의 첫 유효 성적
        "Lee,82\n"       # 4: 정상
        "Kim,99\n",      # 5: 유효한 점수지만 중복 이름
    )

    kept, skipped = load_scores(path)

    assert kept == [("Kim", 75), ("Lee", 82)]
    assert_skipped_rows(skipped, [2, 5])


def test_header_only_is_a_valid_empty_result(tmp_path):
    path = write_csv(tmp_path, "name,score\n")

    assert load_scores(path) == ([], [])


@pytest.mark.parametrize(
    "content",
    [
        "",
        "Kim,80\n",
        "score,name\n80,Kim\n",
        "name,grade\nKim,80\n",
        "name,score,extra\nKim,80,x\n",
    ],
    ids=["empty-file", "no-header", "swapped-columns", "wrong-column-name", "extra-column"],
)
def test_invalid_or_missing_header_raises(tmp_path, content):
    path = write_csv(tmp_path, content)

    with pytest.raises(ValueError):
        load_scores(path)


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_scores(tmp_path / "missing.csv")


def test_directory_path_raises(tmp_path):
    directory = tmp_path / "folder"
    directory.mkdir()

    # 디렉터리를 열 때의 구체적인 예외는 운영체제마다 다를 수 있다.
    with pytest.raises(OSError):
        load_scores(directory)