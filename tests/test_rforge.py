from agy.plugins.rforge import RForgeBridge


def test_is_r_package_true(tmp_path):
    (tmp_path / "DESCRIPTION").write_text("Package: testpkg\nVersion: 0.1.0\n")
    bridge = RForgeBridge(str(tmp_path))
    assert bridge.is_r_package() is True


def test_is_r_package_false(tmp_path):
    bridge = RForgeBridge(str(tmp_path))
    assert bridge.is_r_package() is False


def test_check_package_not_r_package(tmp_path):
    bridge = RForgeBridge(str(tmp_path))
    res = bridge.check_package()
    assert res["success"] is False
    assert "is not an R package" in res["error"]


def test_check_package_success(tmp_path, mocker):
    (tmp_path / "DESCRIPTION").write_text("Package: testpkg\n")
    bridge = RForgeBridge(str(tmp_path))

    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "Check passed"
    mock_run.return_value.stderr = ""

    res = bridge.check_package()
    assert res["success"] is True
    assert res["error"] is None
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "devtools::check" in args[-1]


def test_test_package_failure(tmp_path, mocker):
    (tmp_path / "DESCRIPTION").write_text("Package: testpkg\n")
    bridge = RForgeBridge(str(tmp_path))

    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.returncode = 1
    mock_run.return_value.stdout = "Test failures"
    mock_run.return_value.stderr = "Error in test"

    res = bridge.test_package()
    assert res["success"] is False
    assert res["error"] == "R execution failed."
    assert res["returncode"] == 1
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "devtools::test" in args[-1]


def test_document_package_success(tmp_path, mocker):
    (tmp_path / "DESCRIPTION").write_text("Package: testpkg\n")
    bridge = RForgeBridge(str(tmp_path))

    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "Documented"
    mock_run.return_value.stderr = ""

    res = bridge.document_package()
    assert res["success"] is True
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "devtools::document" in args[-1]
