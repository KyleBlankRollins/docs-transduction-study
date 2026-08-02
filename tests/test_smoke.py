from docs_transduction_study import main


def test_package_entry_point_is_callable() -> None:
    assert callable(main)
