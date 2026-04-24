import re

with open('webui/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_routes = """\
    app.router.add_post("/api/lazy/batch_fate", api_lazy_batch_fate)
    app.router.add_post("/api/lazy/batch_func", api_lazy_batch_func)
    app.router.add_post("/api/lazy/auto_bind", api_lazy_auto_bind)

    # 专门挂载隔离的外网图片目录
    app.router.add_static("/lazy_assets/fate", BASE_PATHS["plugin_data_dir"] / "lazy_images" / "fate")
    app.router.add_static("/lazy_assets/func", BASE_PATHS["plugin_data_dir"] / "lazy_images" / "func")
"""

# 替换底部的路由
content = re.sub(r'\s*app\.router\.add_post\("/api/lazy/match"[^\n]*\n\s*app\.router\.add_post\("/api/lazy/batch_fate"[^\n]*\n\s*app\.router\.add_post\("/api/lazy/batch_func"[^\n]*', '\n' + new_routes, content)

with open('webui/server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Routes patched.")
