# Esc 在 edit / preview 模式統一行為：sidebar 隱藏→離開確認，sidebar 可見→highlight 目前檔案

## Context

目前 Esc 行為在兩種模式下不一致：

- **Edit 模式** (`RichedTextArea._on_key`, `src/rich_editor/editor.py:58-68`)：sidebar 隱藏時按 Esc 觸發離開確認；sidebar 可見時 **fall through**（什麼都不做）。
- **Preview 模式** (`RichedMarkdownViewer`, `src/rich_editor/app.py:367-386`)：Esc 無條件呼叫 `action_focus_sidebar`，所以隱藏時會把 sidebar 叫出來、可見時只是 focus（游標停在原處，不會指向目前開啟的檔案）。

使用者要的統一行為（編輯器或預覽取得焦點時按 Esc）：

1. **sidebar 隱藏** → 跳出離開程式的確認（沿用既有 `action_sidebar_quit_check`）。
2. **sidebar 可見** → 聚焦 sidebar 並把 tree 游標移到（highlight）目前開啟的檔案 `self.path`，必要時展開其上層資料夾。**不可重新開啟檔案**（不能觸發 `DirectoryTree.FileSelected`）。

注意：當焦點在 sidebar tree 本身時，Esc 維持既有 `quit_check` 行為（`RichedDirectoryTree` 的 `escape` binding，`app.py:269`），本次不更動。

## 需要的新功能：在 tree 中 reveal/highlight 目前檔案

Textual 的 `DirectoryTree` **沒有**內建 reveal-by-path，且子資料夾是非同步 lazy-load 的（`_add_to_load_queue(node)` 回傳可 await 的 `AwaitComplete`，await 後 children 才填入）。因此需自行實作逐層展開 + 等待載入。

### 改動 1：`RichedDirectoryTree` 新增 reveal 方法（`src/rich_editor/app.py:255` 類別內）

```python
def reveal_path(self, target: Path) -> None:
    """聚焦目前檔案在 tree 中的節點，必要時展開上層資料夾。不重開檔案。"""
    self.run_worker(self._reveal_path(target), exclusive=True, group="reveal")

async def _reveal_path(self, target: Path) -> None:
    root_entry = self.root.data
    if root_entry is None:
        return
    try:
        rel = target.resolve().relative_to(root_entry.path.resolve())
    except (ValueError, OSError):
        return  # 不在 workspace root 底下，略過
    node = self.root
    if not node.is_expanded:
        node.expand()
    await self._add_to_load_queue(node)
    for index, part in enumerate(rel.parts):
        match = next(
            (c for c in node.children
             if c.data is not None and c.data.path.name == part),
            None,
        )
        if match is None:
            return  # 找不到（已刪除/尚未載入），放棄
        node = match
        if index < len(rel.parts) - 1:  # 中間層才需展開載入
            if not node.is_expanded:
                node.expand()
            await self._add_to_load_queue(node)
    self.move_cursor(node, animate=False)  # 用 move_cursor 而非 select_node，避免重開檔案
```

設計重點：
- 用 `move_cursor`（會自動 scroll 進視野），**不用** `select_node`（會發 `NodeSelected` → 重開檔案）。
- `_add_to_load_queue` 具 `loaded` 旗標冪等性，與 expand handler 重複入列不會 race；await 其回傳值可確保 children 已填入再讀 `node.children`。
- 逐層 name 比對相對路徑，避開 symlink/絕對相對混用問題。
- guard：root.data 為 None、target 不在 root 下、節點找不到 → 安靜返回。
- `_add_to_load_queue` 為 base class 內部方法但其 docstring 即說明回傳值可 await；屬可接受的合理依賴。

### 改動 2：App 統一 Esc 入口（`src/rich_editor/app.py`，`RichedApp` 內）

新增方法（取代 preview 目前呼叫的 `action_focus_sidebar` 流程）：

```python
def action_sidebar_escape(self) -> None:
    if not self._is_sidebar_visible():
        self.action_sidebar_quit_check()
        return
    tree = self._sidebar()
    tree.focus()
    if isinstance(tree, RichedDirectoryTree) and self.path is not None:
        tree.reveal_path(self.path)
```

檢查 `action_focus_sidebar`（`app.py:1603-1606`）是否仍有其他呼叫者：若僅 preview 使用，改為被 `action_sidebar_escape` 取代後可一併移除；若他處仍用則保留。

### 改動 3：Edit 模式（`src/rich_editor/editor.py:58-68`）

把「僅隱藏時處理、可見時 fall through」改為一律交給統一入口：

```python
async def _on_key(self, event: events.Key) -> None:
    if event.key == "escape":
        from .app import RichedApp
        app = self.app
        if isinstance(app, RichedApp):
            app.action_sidebar_escape()
            event.stop()
            event.prevent_default()
            return
    await super()._on_key(event)
```

### 改動 4：Preview 模式（`src/rich_editor/app.py:370-386`）

把 `escape` binding 指向統一入口，移除舊的 `action_focus_sidebar` 包裝：

```python
BINDINGS = [
    *MarkdownViewer.BINDINGS,
    Binding("escape", "sidebar_escape", "Sidebar / quit", show=False),
]

def action_sidebar_escape(self) -> None:
    app = self.app
    if isinstance(app, RichedApp):
        app.action_sidebar_escape()
```

`bindings.yaml` 不需更動（preview 的 escape 是程式內 Binding）。

## 驗證

`uv run riched <path>` 手動測試：

1. **Edit + sidebar 隱藏**：`--edit` 開檔，Esc → 跳出離開確認。
2. **Edit + sidebar 可見**：`cmd+b` 顯示 sidebar，焦點在編輯器，Esc → 焦點移到 sidebar 且游標停在目前檔案（非 fall through、非重開檔案）。
3. **Preview + sidebar 隱藏**：開 markdown（預設 preview、sidebar 隱藏），Esc → 跳出離開確認（不再叫出 sidebar）。
4. **Preview + sidebar 可見**：顯示 sidebar 後回到 preview，Esc → 焦點移到 sidebar 且游標停在目前檔案。
5. **巢狀檔案**：開啟位於子資料夾的檔案，sidebar 可見時 Esc → 自動展開上層資料夾並 highlight，且確認不會重新觸發開檔。
6. **tree 取得焦點時** Esc 仍為離開確認（既有行為未被破壞）。
7. e2e：若 `tests/`（Textual Pilot）有相關測試，跑 `uv run python -m tests.runner` 確認無回歸；依規範用 headless-browser 規則不適用此 TUI，改以 Pilot 新增涵蓋上述分流的 e2e 測試，並更新 `e2e.md`（若存在）。
