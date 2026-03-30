# 把卡牌编辑器区域改成模态框
with open('webui/static/index.html', encoding='utf-8') as f:
    content = f.read()

if 'card-modal' in content:
    print('已经是模态框版本，跳过')
else:
    start_marker = '<div class="editor-layout">'
    start = content.find(start_marker)
    anchor = '允许同名牌，便于做同效果不同卡面版本。'
    anchor_pos = content.find(anchor)
    pos = anchor_pos
    close_count = 0
    while close_count < 4 and pos < len(content):
        idx = content.find('</div>', pos)
        if idx == -1:
            break
        pos = idx + 6
        close_count += 1
    end = pos
    print('block length:', end - start)

    new_block = """<!-- 卡牌编辑模态框 -->
          <div class=\"modal-overlay hidden\" id=\"card-modal\" onclick=\"if(event.target.id==='card-modal')closeCardModal()\">
            <div class=\"modal-box\">
              <div class=\"modal-header\">
                <h2 id=\"card-modal-title\">🎴 新增卡牌</h2>
                <button class=\"modal-close\" onclick=\"closeCardModal()\">×</button>
              </div>
              <div class=\"editor-layout\">
                <div>
                  <div class=\"form-grid\">
                    <div class=\"field\"><label>卡牌名称</label><input id=\"edit-card-name\" placeholder=\"例如：命运转盘\" /></div>
                    <div class=\"field\"><label>卡牌类型</label><select id=\"edit-card-type\"><option value=\"attack\">攻击</option><option value=\"heal\">治疗</option><option value=\"defense\">防御</option></select></div>
                    <div class=\"field\"><label>稀有度</label><select id=\"edit-card-rarity\"><option value=\"1\">1 - 普通</option><option value=\"2\">2 - 稀有</option><option value=\"3\">3 - 史诗</option><option value=\"4\">4 - 传说</option><option value=\"5\">5 - 神话</option></select></div>
                    <div class=\"field\"><label>图片</label><select id=\"edit-card-filename-select\"><option value=\"\">不绑定图片</option></select><input id=\"edit-card-filename\" placeholder=\"或手动输入文件名\" style=\"margin-top:8px;\" /></div>
                    <div class=\"field full\"><label>描述</label><textarea id=\"edit-card-desc\" rows=\"3\" placeholder=\"输入这张牌的效果描述...\"></textarea></div>
                  </div>
                  <h3 class=\"sub-title\" style=\"margin-top:18px;\">🧩 Tag 可视化构建</h3>
                  <div class=\"form-grid\">
                    <div class=\"field\"><label>功能分类</label><select id=\"tag-category\"><option value=\"\">选择分类</option><option value=\"attack\">攻击 / 掠夺 / 控制</option><option value=\"heal\">治疗 / 辅助</option><option value=\"defense\">防御 / 状态</option><option value=\"aoe\">群体效果</option><option value=\"dice\">骰子规则</option></select></div>
                    <div class=\"field\"><label>具体词条</label><select id=\"tag-template\"><option value=\"\">先选择分类</option></select></div>
                  </div>
                  <div id=\"tag-params\" class=\"form-grid\"></div>
                  <div class=\"toolbar\" style=\"margin-top:12px;\"><button class=\"btn\" id=\"btn-add-tag\">添加词条</button></div>
                  <div id=\"current-tags\" style=\"display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;\"></div>
                  <div class=\"toolbar\" style=\"margin-top:18px;\">
                    <button class=\"btn\" id=\"btn-save-card\">保存这张卡</button>
                    <button class=\"btn-ghost\" id=\"btn-copy-card\">复制当前卡</button>
                    <button class=\"btn-danger\" id=\"btn-delete-card\">删除当前卡</button>
                  </div>
                </div>
                <div>
                  <h3 class=\"sub-title\">🔮 实时预览</h3>
                  <div class=\"preview-box\" id=\"card-preview-box\">选择或创建一张牌后，这里会显示卡面预览。</div>
                  <div class=\"footer-note\">• 预览仅影响 WebUI 显示，不影响 Bot 实际发图。<br>• 允许同名牌，便于做同效果不同卡面版本。</div>
                </div>
              </div>
            </div>
          </div>"""

    new_content = content[:start] + new_block + content[end:]
    with open('webui/static/index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('done, new length:', len(new_content))
