from video_admire.taxonomy import DEFAULT_ISSUE_TAGS


def test_out_of_frame_reentry_id_change_is_a_default_issue_type() -> None:
    assert "目标移动出画面后重新给予新编号" in DEFAULT_ISSUE_TAGS
    assert len(DEFAULT_ISSUE_TAGS) == len(set(DEFAULT_ISSUE_TAGS))
