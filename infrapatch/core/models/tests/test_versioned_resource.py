from pathlib import Path, PosixPath

import pytest

from infrapatch.core.models.versioned_resource import ResourceStatus, VersionedResource


def test_version_management():
    # Create new resource with newer version
    resource = VersionedResource(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), start_line_number=1)
    resource.newest_version = "2.0.0"

    assert resource.status == ResourceStatus.UNPATCHED
    assert resource.installed_version_equal_or_newer_than_new_version() is False

    resource.set_patched()
    assert resource.status == ResourceStatus.PATCHED

    # Check new_version the same as current_version
    resource = VersionedResource(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), start_line_number=1)
    resource.newest_version = "1.0.0"

    assert resource.status == ResourceStatus.UP_TO_DATE
    assert resource.installed_version_equal_or_newer_than_new_version() is True

    # Check new_version older than current_version
    resource = VersionedResource(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), start_line_number=1)
    resource.newest_version = "0.1.0"

    assert resource.status == ResourceStatus.UP_TO_DATE
    assert resource.installed_version_equal_or_newer_than_new_version() is True


def test_tile_constraint():
    resource = VersionedResource(name="test_resource", current_version="~>1.0.0", source_file=Path("test_file.py"), start_line_number=1)
    resource.newest_version = "~>1.0.1"
    assert resource.has_tile_constraint() is True
    assert resource.installed_version_equal_or_newer_than_new_version() is True

    resource.newest_version = "~>1.1.0"
    assert resource.installed_version_equal_or_newer_than_new_version() is False

    resource = VersionedResource(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), start_line_number=1)
    assert resource.has_tile_constraint() is False

    resource = VersionedResource(name="test_resource", current_version="~>1.0.0", source_file=Path("test_file.py"), start_line_number=1)
    resource.newest_version = "1.1.0"
    assert resource.newest_version == "~>1.1.0"


def test_git_repo():
    resource = VersionedResource(name="test_resource", current_version="~>1.0.0", source_file=Path("test_file.py"), start_line_number=1)

    assert resource.github_repo is None

    resource.github_repo = "https://github.com/noahnc/test_repo.git"
    assert resource.github_repo == "noahnc/test_repo"

    resource.github_repo = "https://github.com/noahnc/test_repo"
    assert resource.github_repo == "noahnc/test_repo"

    with pytest.raises(Exception):
        resource.github_repo = "https://github.com/"

    with pytest.raises(Exception):
        resource.github_repo = "https://github.com"


def test_patch_error():
    resource = VersionedResource(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), start_line_number=1)
    resource.set_patch_error()
    assert resource.status == ResourceStatus.PATCH_ERROR


def test_version_not_found():
    # Test manual setting
    resource = VersionedResource(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), start_line_number=1)
    resource.set_no_version_found()
    assert resource.status == ResourceStatus.NO_VERSION_FOUND
    assert resource.installed_version_equal_or_newer_than_new_version() is True

    # Test by setting None as new version
    resource = VersionedResource(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), start_line_number=1)
    resource.newest_version = None
    assert resource.status == ResourceStatus.NO_VERSION_FOUND
    assert resource.installed_version_equal_or_newer_than_new_version() is True


def test_path():
    resource = VersionedResource(name="test_resource", current_version="1.0.0", source_file=Path("/var/testdir/test_file.py"), start_line_number=1)
    assert resource.source_file == Path("/var/testdir/test_file.py")


def test_find():
    findably_resource = VersionedResource(name="test_resource3", current_version="1.0.0", source_file=Path("test_file3.py"), start_line_number=1)
    unfindably_resource = VersionedResource(name="test_resource6", current_version="1.0.0", source_file=Path("test_file8.py"), start_line_number=1)
    resources = [
        VersionedResource(name="test_resource1", current_version="1.0.0", source_file=Path("test_file1.py"), start_line_number=1),
        VersionedResource(name="test_resource2", current_version="1.0.0", source_file=Path("test_file2.py"), start_line_number=1),
        VersionedResource(name="test_resource3", current_version="1.0.0", source_file=Path("test_file3.py"), start_line_number=1),
        VersionedResource(name="test_resource4", current_version="1.0.0", source_file=Path("test_file4.py"), start_line_number=1),
        VersionedResource(name="test_resource5", current_version="1.0.0", source_file=Path("test_file5.py"), start_line_number=1),
    ]
    assert len(findably_resource.find(resources)) == 1
    assert findably_resource.find(resources) == [resources[2]]
    assert len(unfindably_resource.find(resources)) == 0


def test_versioned_resource_to_dict():
    resource = VersionedResource(name="test_resource", current_version="1.0.0", source_file=Path("test_file.py"), start_line_number=1)
    expected_dict = {
        "name": "test_resource",
        "current_version": "1.0.0",
        "source_file": PosixPath("test_file.py"),
        "newest_version_string": None,
        "status": ResourceStatus.UNPATCHED,
        "github_repo_string": None,
        "start_line_number": 1,
        "options": {
            "ignore_resource": False,
        },
    }
    assert resource.model_dump() == expected_dict
