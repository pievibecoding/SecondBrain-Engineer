def test_internal_nas_router_imports():
    from backend.routers.internal import nas

    assert nas.router is not None


def test_internal_nas_helpers_exist():
    from backend.routers.internal.nas import get_nas_file_by_path, get_nas_file_by_id, find_folder_by_path

    assert callable(get_nas_file_by_path)
    assert callable(get_nas_file_by_id)
    assert callable(find_folder_by_path)
