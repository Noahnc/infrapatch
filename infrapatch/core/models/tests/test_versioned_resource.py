from pathlib import Path

from infrapatch.core.models.versioned_resource import ResourceStatus, VersionedResource


def test_version_management():
    # Create new resource with newer version
    resource = VersionedResource(name="test_resource", current_version="1.0.0", _source_file="test_file.py")
    resource.newest_version = "2.0.0"

    assert resource.status == ResourceStatus.UNPATCHED
    assert resource.installed_version_equal_or_newer_than_new_version() is False

    resource.set_patched()
    assert resource.status == ResourceStatus.PATCHED

    resource = VersionedResource(name="test_resource", current_version="1.0.0", _source_file="test_file.py")
    resource.newest_version = "1.0.0"

    assert resource.status == ResourceStatus.UNPATCHED
    assert resource.installed_version_equal_or_newer_than_new_version() is True


def test_tile_constraint():
    resource = VersionedResource(name="test_resource", current_version="~>1.0.0", _source_file="test_file.py")
    resource.newest_version = "~>1.0.1"
    assert resource.has_tile_constraint() is True
    assert resource.installed_version_equal_or_newer_than_new_version() is True

    resource.newest_version = "~>1.1.0"
    assert resource.installed_version_equal_or_newer_than_new_version() is False

    resource = VersionedResource(name="test_resource", current_version="1.0.0", _source_file="test_file.py")
    assert resource.has_tile_constraint() is False

    resource = VersionedResource(name="test_resource", current_version="~>1.0.0", _source_file="test_file.py")
    resource.newest_version = "1.1.0"
    assert resource.newest_version == "~>1.1.0"


def test_patch_error():
    resource = VersionedResource(name="test_resource", current_version="1.0.0", _source_file="test_file.py")
    resource.set_patch_error()
    assert resource.status == ResourceStatus.PATCH_ERROR


def test_path():
    resource = VersionedResource(name="test_resource", current_version="1.0.0", _source_file="/var/testdir/test_file.py")
    assert resource.source_file == Path("/var/testdir/test_file.py")


def test_find():
    findably_resource = VersionedResource(name="test_resource3", current_version="1.0.0", _source_file="test_file3.py")
    unfindably_resource = VersionedResource(name="test_resource6", current_version="1.0.0", _source_file="test_file8.py")
    resources = [
        VersionedResource(name="test_resource1", current_version="1.0.0", _source_file="test_file1.py"),
        VersionedResource(name="test_resource2", current_version="1.0.0", _source_file="test_file2.py"),
        VersionedResource(name="test_resource3", current_version="1.0.0", _source_file="test_file3.py"),
        VersionedResource(name="test_resource4", current_version="1.0.0", _source_file="test_file4.py"),
        VersionedResource(name="test_resource5", current_version="1.0.0", _source_file="test_file5.py"),
    ]
    assert len(findably_resource.find(resources)) == 1
    assert findably_resource.find(resources) == [resources[2]]
    assert len(unfindably_resource.find(resources)) == 0


def test_versioned_resource_to_dict():
    resource = VersionedResource(name="test_resource", current_version="1.0.0", _source_file="test_file.py")
    expected_dict = {"name": "test_resource", "current_version": "1.0.0", "_source_file": "test_file.py", "_newest_version": None, "_status": ResourceStatus.UNPATCHED}
    assert resource.to_dict() == expected_dict
