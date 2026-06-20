def test_admin_nas_folders_router_imports():
    from backend.routers.admin import nas_folders

    assert nas_folders.router is not None
