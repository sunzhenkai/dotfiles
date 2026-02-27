# keymap

references:

1. https://gist.github.com/oca159/0b480ed6555056418905b6e59af33674
2. https://github.com/mrnugget/dotfiles/blob/master/zed_keymap.json

## Context

- Workspace
- Editor
- Terminal

# settings

Zed settings

For information on how to configure Zed, see the Zed
documentation: https://zed.dev/docs/configuring-zed

To see all of Zed's default settings without changing your
custom settings, run `zed: open default settings` from the
command palette (cmd-shift-p / ctrl-shift-p)

# Action

以下是 Zed 中所有可用的 action 列表，按功能分类组织。

## Workspace（工作区）

- `workspace::ToggleLeftDock` - 切换左侧面板
- `workspace::ToggleRightDock` - 切换右侧面板
- `workspace::ToggleBottomDock` - 切换底部面板
- `workspace::ToggleAllDocks` - 切换所有面板
- `workspace::CloseAllDocks` - 关闭所有面板
- `workspace::CloseActiveDock` - 关闭当前活动面板
- `workspace::IncreaseOpenDocksSize` - 增大所有打开面板的大小
- `workspace::DecreaseOpenDocksSize` - 减小所有打开面板的大小
- `workspace::IncreaseActiveDockSize` - 增大当前活动面板的大小
- `workspace::DecreaseActiveDockSize` - 减小当前活动面板的大小
- `workspace::ResetOpenDocksSize` - 重置所有打开面板的大小
- `workspace::ResetActiveDockSize` - 重置当前活动面板的大小
- `workspace::NewFile` - 新建文件
- `workspace::NewFileSplit` - 在新窗格中新建文件
- `workspace::NewFileSplitVertical` - 在垂直分割窗格中新建文件
- `workspace::NewFileSplitHorizontal` - 在水平分割窗格中新建文件
- `workspace::NewWindow` - 新建窗口
- `workspace::NewTerminal` - 新建终端
- `workspace::NewCenterTerminal` - 在中心区域新建终端
- `workspace::Open` - 打开文件
- `workspace::OpenFiles` - 打开多个文件
- `workspace::OpenTerminal` - 打开终端
- `workspace::OpenInTerminal` - 在终端中打开
- `workspace::OpenWithSystem` - 使用系统默认程序打开
- `workspace::Save` - 保存
- `workspace::SaveAs` - 另存为
- `workspace::SaveAll` - 保存所有
- `workspace::SaveWithoutFormat` - 保存（不格式化）
- `workspace::Reload` - 重新加载
- `workspace::ReloadActiveItem` - 重新加载当前项
- `workspace::CloseWindow` - 关闭窗口
- `workspace::CloseProject` - 关闭项目
- `workspace::CloseItemInAllPanes` - 在所有窗格中关闭项目
- `workspace::CloseInactiveTabsAndPanes` - 关闭非活动标签页和窗格
- `workspace::CloseAllItemsAndPanes` - 关闭所有项目和窗格
- `workspace::AddFolderToProject` - 添加文件夹到项目
- `workspace::ActivateNextPane` - 激活下一个窗格
- `workspace::ActivatePreviousPane` - 激活上一个窗格
- `workspace::ActivatePane` - 激活指定窗格
- `workspace::ActivatePaneLeft` - 激活左侧窗格
- `workspace::ActivatePaneRight` - 激活右侧窗格
- `workspace::ActivatePaneUp` - 激活上方窗格
- `workspace::ActivatePaneDown` - 激活下方窗格
- `workspace::MovePaneLeft` - 向左移动窗格
- `workspace::MovePaneRight` - 向右移动窗格
- `workspace::MovePaneUp` - 向上移动窗格
- `workspace::MovePaneDown` - 向下移动窗格
- `workspace::SwapPaneLeft` - 与左侧窗格交换
- `workspace::SwapPaneRight` - 与右侧窗格交换
- `workspace::SwapPaneUp` - 与上方窗格交换
- `workspace::SwapPaneDown` - 与下方窗格交换
- `workspace::SwapPaneAdjacent` - 与相邻窗格交换
- `workspace::MoveItemToPane` - 移动项目到指定窗格
- `workspace::MoveItemToPaneInDirection` - 向指定方向移动项目到窗格
- `workspace::ActivateNextWindow` - 激活下一个窗口
- `workspace::ActivatePreviousWindow` - 激活上一个窗口
- `workspace::ToggleZoom` - 切换缩放
- `workspace::ZoomIn` - 放大
- `workspace::ZoomOut` - 缩小
- `workspace::ToggleCenteredLayout` - 切换居中布局
- `workspace::ToggleReadOnlyFile` - 切换只读模式
- `workspace::ToggleEditPrediction` - 切换编辑预测
- `workspace::ToggleWorktreeSecurity` - 切换工作树安全性
- `workspace::FollowNextCollaborator` - 关注下一个协作者
- `workspace::Unfollow` - 取消关注
- `workspace::CopyPath` - 复制路径
- `workspace::CopyRelativePath` - 复制相对路径
- `workspace::NewSearch` - 新建搜索
- `workspace::SendKeystrokes` - 发送按键
- `workspace::ClearNavigationHistory` - 清除导航历史
- `workspace::RestoreBanner` - 恢复横幅
- `workspace::SuppressNotification` - 抑制通知
- `workspace::Feedback` - 反馈
- `workspace::OpenComponentPreview` - 打开组件预览
- `workspace::ClearTrustedWorktrees` - 清除信任的工作树

## Pane（窗格）

- `pane::SplitDown` - 向下分割
- `pane::SplitUp` - 向上分割
- `pane::SplitLeft` - 向左分割
- `pane::SplitRight` - 向右分割
- `pane::SplitHorizontal` - 水平分割
- `pane::SplitVertical` - 垂直分割
- `pane::SplitAndMoveDown` - 分割并向下移动
- `pane::SplitAndMoveUp` - 分割并向上移动
- `pane::SplitAndMoveLeft` - 分割并向左移动
- `pane::SplitAndMoveRight` - 分割并向右移动
- `pane::ActivateNextItem` - 激活下一个项目
- `pane::ActivatePreviousItem` - 激活上一个项目
- `pane::ActivateLastItem` - 激活最后一个项目
- `pane::CloseActiveItem` - 关闭活动项目
- `pane::CloseOtherItems` - 关闭其他项目
- `pane::CloseInactiveItems` - 关闭非活动项目
- `pane::CloseAllItems` - 关闭所有项目
- `pane::CloseCleanItems` - 关闭干净的项目
- `pane::CloseItemsToTheLeft` - 关闭左侧项目
- `pane::CloseItemsToTheRight` - 关闭右侧项目
- `pane::CloseMultibufferItems` - 关闭多缓冲区项目
- `pane::ReopenClosedItem` - 重新打开已关闭的项目
- `pane::SwapItemLeft` - 向左交换项目
- `pane::SwapItemRight` - 向右交换项目
- `pane::GoBack` - 后退
- `pane::GoForward` - 前进
- `pane::GoToNewerTag` - 转到较新的标签
- `pane::GoToOlderTag` - 转到较旧的标签
- `pane::AlternateFile` - 切换文件
- `pane::TogglePinTab` - 切换固定标签
- `pane::TogglePreviewTab` - 切换预览标签
- `pane::UnpinAllTabs` - 取消固定所有标签
- `pane::JoinAll` - 合并所有
- `pane::JoinIntoNext` - 合并到下一个
- `pane::RevealInProjectPanel` - 在项目面板中显示
- `pane::DeploySearch` - 部署搜索

## Editor（编辑器）

### 导航
- `editor::MoveUp` - 向上移动
- `editor::MoveDown` - 向下移动
- `editor::MoveLeft` - 向左移动
- `editor::MoveRight` - 向右移动
- `editor::MoveToBeginning` - 移动到开头
- `editor::MoveToEnd` - 移动到结尾
- `editor::MoveToBeginningOfLine` - 移动到行首
- `editor::MoveToEndOfLine` - 移动到行尾
- `editor::MoveToPreviousWordStart` - 移动到上一个单词开头
- `editor::MoveToNextWordEnd` - 移动到下一个单词结尾
- `editor::MoveToPreviousSubwordStart` - 移动到上一个子单词开头
- `editor::MoveToNextSubwordEnd` - 移动到下一个子单词结尾
- `editor::MoveToStartOfParagraph` - 移动到段落开头
- `editor::MoveToEndOfParagraph` - 移动到段落结尾
- `editor::MovePageUp` - 向上翻页
- `editor::MovePageDown` - 向下翻页
- `editor::MoveUpByLines` - 按行数向上移动
- `editor::MoveDownByLines` - 按行数向下移动
- `editor::LineUp` - 行向上
- `editor::LineDown` - 行向下
- `editor::ScrollCursorTop` - 滚动光标到顶部
- `editor::ScrollCursorBottom` - 滚动光标到底部
- `editor::ScrollCursorCenter` - 滚动光标到中心
- `editor::ScrollCursorCenterTopBottom` - 滚动光标到中心/顶部/底部

### 选择
- `editor::SelectAll` - 全选
- `editor::SelectUp` - 向上选择
- `editor::SelectDown` - 向下选择
- `editor::SelectLeft` - 向左选择
- `editor::SelectRight` - 向右选择
- `editor::SelectToBeginning` - 选择到开头
- `editor::SelectToEnd` - 选择到结尾
- `editor::SelectToBeginningOfLine` - 选择到行首
- `editor::SelectToEndOfLine` - 选择到行尾
- `editor::SelectLine` - 选择行
- `editor::SelectAllMatches` - 选择所有匹配
- `editor::SelectNext` - 选择下一个
- `editor::SelectPrevious` - 选择上一个
- `editor::SelectLargerSyntaxNode` - 选择更大的语法节点
- `editor::SelectSmallerSyntaxNode` - 选择更小的语法节点
- `editor::SelectNextSyntaxNode` - 选择下一个语法节点
- `editor::SelectPreviousSyntaxNode` - 选择上一个语法节点
- `editor::SelectEnclosingSymbol` - 选择包围符号
- `editor::AddSelectionAbove` - 在上方添加选择
- `editor::AddSelectionBelow` - 在下方添加选择
- `editor::SplitSelectionIntoLines` - 将选择分割成行
- `editor::RotateSelectionsForward` - 向前旋转选择
- `editor::RotateSelectionsBackward` - 向后旋转选择
- `editor::SwapSelectionEnds` - 交换选择端点

### 编辑
- `editor::Delete` - 删除
- `editor::Backspace` - 退格
- `editor::DeleteLine` - 删除行
- `editor::DeleteToBeginningOfLine` - 删除到行首
- `editor::DeleteToEndOfLine` - 删除到行尾
- `editor::DeleteToPreviousWordStart` - 删除到上一个单词开头
- `editor::DeleteToNextWordEnd` - 删除到下一个单词结尾
- `editor::DeleteToPreviousSubwordStart` - 删除到上一个子单词开头
- `editor::DeleteToNextSubwordEnd` - 删除到下一个子单词结尾
- `editor::Tab` - Tab 键
- `editor::Backtab` - 反向 Tab
- `editor::Newline` - 新行
- `editor::NewlineAbove` - 在上方新建行
- `editor::NewlineBelow` - 在下方新建行
- `editor::Indent` - 缩进
- `editor::Outdent` - 取消缩进
- `editor::AutoIndent` - 自动缩进
- `editor::JoinLines` - 合并行
- `editor::Transpose` - 转置
- `editor::DuplicateLineUp` - 向上复制行
- `editor::DuplicateLineDown` - 向下复制行
- `editor::DuplicateSelection` - 复制选择
- `editor::MoveLineUp` - 向上移动行
- `editor::MoveLineDown` - 向下移动行
- `editor::SortLinesCaseSensitive` - 排序行（区分大小写）
- `editor::SortLinesCaseInsensitive` - 排序行（不区分大小写）
- `editor::SortLinesByLength` - 按长度排序行
- `editor::ReverseLines` - 反转行
- `editor::ShuffleLines` - 打乱行
- `editor::UniqueLinesCaseSensitive` - 唯一行（区分大小写）
- `editor::UniqueLinesCaseInsensitive` - 唯一行（不区分大小写）
- `editor::ToggleComments` - 切换注释

### 复制粘贴
- `editor::Copy` - 复制
- `editor::Cut` - 剪切
- `editor::Paste` - 粘贴
- `editor::CopyAndTrim` - 复制并修剪
- `editor::CopyFileName` - 复制文件名
- `editor::CopyFileNameWithoutExtension` - 复制文件名（无扩展名）
- `editor::CopyFileLocation` - 复制文件位置
- `editor::CopyPermalinkToLine` - 复制永久链接到行
- `editor::CopyHighlightJson` - 复制高亮 JSON
- `editor::CopyPath` - 复制路径
- `editor::CopyRelativePath` - 复制相对路径
- `editor::KillRingCut` - Kill ring 剪切
- `editor::KillRingYank` - Kill ring 粘贴

### 格式化
- `editor::Format` - 格式化
- `editor::FormatSelections` - 格式化选择
- `editor::Rewrap` - 重排
- `editor::ConvertToLowerCase` - 转换为小写
- `editor::ConvertToUpperCase` - 转换为大写
- `editor::ConvertToOppositeCase` - 转换为相反大小写
- `editor::ConvertToTitleCase` - 转换为标题大小写
- `editor::ConvertToLowerCamelCase` - 转换为小驼峰
- `editor::ConvertToUpperCamelCase` - 转换为大驼峰
- `editor::ConvertToSnakeCase` - 转换为蛇形
- `editor::ConvertToKebabCase` - 转换为短横线
- `editor::ConvertToSentenceCase` - 转换为句子大小写
- `editor::ConvertToRot13` - 转换为 ROT13
- `editor::ConvertToRot47` - 转换为 ROT47
- `editor::ConvertIndentationToSpaces` - 转换缩进为空格
- `editor::ConvertIndentationToTabs` - 转换缩进为制表符

### 折叠
- `editor::Fold` - 折叠
- `editor::Unfold` - 展开当前
- `editor::UnfoldAll` - 展开所有
- `editor::UnfoldLines` - 展开行
- `editor::UnfoldRecursive` - 递归展开
- `editor::FoldAll` - 折叠所有
- `editor::FoldRecursive` - 递归折叠
- `editor::FoldFunctionBodies` - 折叠函数体
- `editor::FoldSelectedRanges` - 折叠选中范围
- `editor::ToggleFold` - 切换折叠
- `editor::ToggleFoldAll` - 切换所有折叠
- `editor::ToggleFoldRecursive` - 切换递归折叠
- `editor::FoldAtLevel` - 按级别折叠
- `editor::FoldAtLevel_1` 到 `editor::FoldAtLevel_9` - 按指定级别折叠

### 搜索和替换
- `editor::FindNextMatch` - 查找下一个匹配
- `editor::FindPreviousMatch` - 查找上一个匹配
- `editor::FindAllReferences` - 查找所有引用
- `editor::Replace` - 替换
- `editor::ReplaceNext` - 替换下一个
- `editor::ReplaceAll` - 替换所有

### 导航到定义和引用
- `editor::GoToDefinition` - 转到定义
- `editor::GoToDefinitionSplit` - 在分割窗格中转到定义
- `editor::GoToTypeDefinition` - 转到类型定义
- `editor::GoToTypeDefinitionSplit` - 在分割窗格中转到类型定义
- `editor::GoToImplementation` - 转到实现
- `editor::GoToImplementationSplit` - 在分割窗格中转到实现
- `editor::GoToDeclaration` - 转到声明
- `editor::GoToDeclarationSplit` - 在分割窗格中转到声明
- `editor::GoToParentModule` - 转到父模块
- `editor::GoToHunk` - 转到 Hunk
- `editor::GoToPreviousHunk` - 转到上一个 Hunk
- `editor::GoToNextChange` - 转到下一个更改
- `editor::GoToPreviousChange` - 转到上一个更改
- `editor::GoToNextReference` - 转到下一个引用
- `editor::GoToPreviousReference` - 转到上一个引用
- `editor::GoToNextDocumentHighlight` - 转到下一个文档高亮
- `editor::GoToPreviousDocumentHighlight` - 转到上一个文档高亮
- `editor::GoToDiagnostic` - 转到诊断
- `editor::GoToPreviousDiagnostic` - 转到上一个诊断

### 代码操作
- `editor::ToggleCodeActions` - 切换代码操作
- `editor::ConfirmCodeAction` - 确认代码操作
- `editor::Rename` - 重命名
- `editor::ConfirmRename` - 确认重命名
- `editor::OrganizeImports` - 组织导入
- `editor::Hover` - 悬停
- `editor::ShowCompletions` - 显示补全
- `editor::ShowWordCompletions` - 显示单词补全
- `editor::ConfirmCompletion` - 确认补全
- `editor::ConfirmCompletionInsert` - 确认补全插入
- `editor::ConfirmCompletionReplace` - 确认补全替换
- `editor::ComposeCompletion` - 组合补全
- `editor::ShowSignatureHelp` - 显示签名帮助
- `editor::SignatureHelpNext` - 下一个签名帮助
- `editor::SignatureHelpPrevious` - 上一个签名帮助
- `editor::ShowCharacterPalette` - 显示字符面板
- `editor::ExpandMacroRecursively` - 递归展开宏

### 代码片段
- `editor::InsertSnippet` - 插入代码片段
- `editor::NextSnippetTabstop` - 下一个代码片段停止点
- `editor::PreviousSnippetTabstop` - 上一个代码片段停止点

### 编辑预测
- `editor::ShowEditPrediction` - 显示编辑预测
- `editor::ToggleEditPrediction` - 切换编辑预测
- `editor::AcceptEditPrediction` - 接受编辑预测
- `editor::AcceptNextWordEditPrediction` - 接受下一个单词编辑预测
- `editor::AcceptNextLineEditPrediction` - 接受下一行编辑预测
- `editor::AcceptPartialCopilotSuggestion` - 接受部分 Copilot 建议
- `editor::NextEditPrediction` - 下一个编辑预测
- `editor::PreviousEditPrediction` - 上一个编辑预测

### 显示切换
- `editor::ToggleLineNumbers` - 切换行号
- `editor::ToggleRelativeLineNumbers` - 切换相对行号
- `editor::ToggleIndentGuides` - 切换缩进参考线
- `editor::ToggleInlayHints` - 切换内联提示
- `editor::ToggleSemanticHighlights` - 切换语义高亮
- `editor::ToggleSoftWrap` - 切换软换行
- `editor::ToggleMinimap` - 切换缩略图
- `editor::ToggleTabBar` - 切换标签栏
- `editor::ToggleDiagnostics` - 切换诊断
- `editor::ToggleInlineDiagnostics` - 切换内联诊断
- `editor::ToggleInlineValues` - 切换内联值
- `editor::ToggleHunkDiff` - 切换 Hunk 差异
- `editor::ToggleSelectedDiffHunks` - 切换选中的 Hunk 差异
- `editor::ToggleSplitDiff` - 切换分割差异
- `editor::ToggleFocus` - 切换焦点
- `editor::ToggleAutoSignatureHelp` - 切换自动签名帮助
- `editor::ToggleGitBlame` - 切换 Git Blame
- `editor::ToggleGitBlameInline` - 切换内联 Git Blame
- `editor::ToggleSelectionMenu` - 切换选择菜单

### Git 相关
- `editor::RevertSelectedHunks` - 还原选中的 Hunks
- `editor::RevertFile` - 还原文件
- `editor::OpenGitBlameCommit` - 打开 Git Blame 提交
- `editor::ApplyDiffHunk` - 应用差异 Hunk
- `editor::ApplyAllDiffHunks` - 应用所有差异 Hunks
- `editor::ExpandAllDiffHunks` - 展开所有差异 Hunks
- `editor::CollapseAllDiffHunks` - 折叠所有差异 Hunks
- `editor::ExpandAllHunkDiffs` - 展开所有 Hunk 差异

### 断点
- `editor::ToggleBreakpoint` - 切换断点
- `editor::EnableBreakpoint` - 启用断点
- `editor::DisableBreakpoint` - 禁用断点
- `editor::EditLogBreakpoint` - 编辑日志断点

### 其他
- `editor::Undo` - 撤销
- `editor::Redo` - 重做
- `editor::UndoSelection` - 撤销选择
- `editor::RedoSelection` - 重做选择
- `editor::Cancel` - 取消
- `editor::ReloadFile` - 重新加载文件
- `editor::OpenUrl` - 打开 URL
- `editor::OpenFile` - 打开文件
- `editor::OpenSelectedFilename` - 打开选中的文件名
- `editor::OpenContextMenu` - 打开上下文菜单
- `editor::OpenDocs` - 打开文档
- `editor::OpenExcerpts` - 打开摘录
- `editor::OpenExcerptsSplit` - 在分割窗格中打开摘录
- `editor::OpenPermalinkToLine` - 打开永久链接到行
- `editor::OpenProposedChangesEditor` - 打开建议更改编辑器
- `editor::OpenSelectionsInMultibuffer` - 在多缓冲区中打开选择
- `editor::RevealInFileManager` - 在文件管理器中显示
- `editor::SwitchSourceHeader` - 切换源文件/头文件
- `editor::RestartLanguageServer` - 重启语言服务器
- `editor::StopLanguageServer` - 停止语言服务器
- `editor::CancelLanguageServerWork` - 取消语言服务器工作
- `editor::DisplayCursorNames` - 显示光标名称
- `editor::SetMark` - 设置标记
- `editor::ContextMenuNext` - 下一个上下文菜单项
- `editor::ContextMenuPrevious` - 上一个上下文菜单项
- `editor::ContextMenuFirst` - 第一个上下文菜单项
- `editor::ContextMenuLast` - 最后一个上下文菜单项
- `editor::DiffClipboardWithSelection` - 与剪贴板选择比较差异
- `editor::WrapSelectionsInTag` - 用标签包围选择
- `editor::UnwrapSyntaxNode` - 解包语法节点
- `editor::SpawnNearestTask` - 生成最近的任务
- `editor::InsertUuidV4` - 插入 UUID v4
- `editor::InsertUuidV7` - 插入 UUID v7

## Vim

### 模式切换
- `vim::SwitchToNormalMode` - 切换到普通模式
- `vim::SwitchToInsertMode` - 切换到插入模式
- `vim::SwitchToVisualMode` - 切换到可视模式
- `vim::SwitchToVisualLineMode` - 切换到可视行模式
- `vim::SwitchToVisualBlockMode` - 切换到可视块模式
- `vim::SwitchToReplaceMode` - 切换到替换模式
- `vim::SwitchToHelixNormalMode` - 切换到 Helix 普通模式
- `vim::ToggleVisual` - 切换可视模式
- `vim::ToggleVisualLine` - 切换可视行模式
- `vim::ToggleVisualBlock` - 切换可视块模式
- `vim::ToggleReplace` - 切换替换模式

### 移动
- `vim::Up` - 上
- `vim::Down` - 下
- `vim::Left` - 左
- `vim::Right` - 右
- `vim::LineUp` - 行上
- `vim::LineDown` - 行下
- `vim::ColumnLeft` - 列左
- `vim::ColumnRight` - 列右
- `vim::PageUp` - 向上翻页
- `vim::PageDown` - 向下翻页
- `vim::HalfPageLeft` - 向左半页
- `vim::HalfPageRight` - 向右半页
- `vim::ScrollUp` - 向上滚动
- `vim::ScrollDown` - 向下滚动
- `vim::WindowTop` - 窗口顶部
- `vim::WindowMiddle` - 窗口中间
- `vim::WindowBottom` - 窗口底部
- `vim::StartOfLine` - 行首
- `vim::EndOfLine` - 行尾
- `vim::FirstNonWhitespace` - 第一个非空白字符
- `vim::StartOfParagraph` - 段落开头
- `vim::EndOfParagraph` - 段落结尾
- `vim::StartOfDocument` - 文档开头
- `vim::EndOfDocument` - 文档结尾
- `vim::MiddleOfLine` - 行中间
- `vim::GoToColumn` - 转到列
- `vim::GoToTab` - 转到标签
- `vim::GoToPreviousTab` - 转到上一个标签
- `vim::GoToPercentage` - 转到百分比
- `vim::PreviousWordStart` - 上一个单词开头
- `vim::NextWordStart` - 下一个单词开头
- `vim::PreviousWordEnd` - 上一个单词结尾
- `vim::NextWordEnd` - 下一个单词结尾
- `vim::PreviousSubwordStart` - 上一个子单词开头
- `vim::NextSubwordStart` - 下一个子单词开头
- `vim::PreviousSubwordEnd` - 上一个子单词结尾
- `vim::NextSubwordEnd` - 下一个子单词结尾
- `vim::PreviousLineStart` - 上一行开头
- `vim::NextLineStart` - 下一行开头
- `vim::StartOfLineDownward` - 向下到行首
- `vim::EndOfLineDownward` - 向下到行尾
- `vim::OtherEnd` - 另一端
- `vim::OtherEndRowAware` - 另一端（行感知）
- `vim::PreviousMethodStart` - 上一个方法开头
- `vim::PreviousMethodEnd` - 上一个方法结尾
- `vim::NextMethodStart` - 下一个方法开头
- `vim::NextMethodEnd` - 下一个方法结尾
- `vim::PreviousSectionStart` - 上一个节开头
- `vim::PreviousSectionEnd` - 上一个节结尾
- `vim::NextSectionStart` - 下一个节开头
- `vim::NextSectionEnd` - 下一个节结尾
- `vim::PreviousSameIndent` - 上一个相同缩进
- `vim::NextSameIndent` - 下一个相同缩进
- `vim::PreviousGreaterIndent` - 上一个更大缩进
- `vim::NextGreaterIndent` - 下一个更大缩进
- `vim::PreviousLesserIndent` - 上一个更小缩进
- `vim::NextLesserIndent` - 下一个更小缩进
- `vim::PreviousComment` - 上一个注释
- `vim::NextComment` - 下一个注释

### 插入
- `vim::InsertBefore` - 在之前插入
- `vim::InsertAfter` - 在之后插入
- `vim::InsertLineAbove` - 在上方插入行
- `vim::InsertLineBelow` - 在下方插入行
- `vim::InsertAtPrevious` - 在之前位置插入
- `vim::InsertFirstNonWhitespace` - 在第一个非空白字符插入
- `vim::InsertEndOfLine` - 在行尾插入
- `vim::InsertEmptyLineAbove` - 在上方插入空行
- `vim::InsertEmptyLineBelow` - 在下方插入空行
- `vim::InsertFromAbove` - 从上方插入
- `vim::InsertFromBelow` - 从下方插入
- `vim::TemporaryNormal` - 临时普通模式
- `vim::NormalBefore` - 普通模式之前

### 删除和修改
- `vim::DeleteLeft` - 向左删除
- `vim::DeleteRight` - 向右删除
- `vim::DeleteToEndOfLine` - 删除到行尾
- `vim::Substitute` - 替换
- `vim::SubstituteLine` - 替换行
- `vim::ChangeToEndOfLine` - 修改到行尾
- `vim::VisualDelete` - 可视删除
- `vim::VisualDeleteLine` - 可视删除行
- `vim::HelixDelete` - Helix 删除
- `vim::HelixSubstitute` - Helix 替换
- `vim::HelixSubstituteNoYank` - Helix 替换（不复制）

### 复制和粘贴
- `vim::Yank` - 复制
- `vim::YankLine` - 复制行
- `vim::YankToEndOfLine` - 复制到行尾
- `vim::VisualYank` - 可视复制
- `vim::VisualYankLine` - 可视复制行
- `vim::Paste` - 粘贴
- `vim::HelixYank` - Helix 复制
- `vim::HelixPaste` - Helix 粘贴

### 撤销和重做
- `vim::Undo` - 撤销
- `vim::Redo` - 重做
- `vim::UndoLastLine` - 撤销最后一行
- `vim::UndoReplace` - 撤销替换

### 缩进
- `vim::Indent` - 缩进
- `vim::Outdent` - 取消缩进
- `vim::AutoIndent` - 自动缩进

### 搜索
- `vim::Search` - 搜索
- `vim::SearchUnderCursor` - 搜索光标下的内容
- `vim::SearchUnderCursorPrevious` - 搜索光标下的内容（上一个）
- `vim::SearchSubmit` - 提交搜索
- `vim::RepeatFind` - 重复查找
- `vim::RepeatFindReversed` - 反向重复查找
- `vim::SelectNextMatch` - 选择下一个匹配
- `vim::SelectPreviousMatch` - 选择上一个匹配

### 寄存器和宏
- `vim::SelectRegister` - 选择寄存器
- `vim::ToggleRecord` - 切换录制
- `vim::Repeat` - 重复
- `vim::EndRepeat` - 结束重复
- `vim::ReplayLastRecording` - 重放上次录制

### 对象和文本对象
- `vim::Word` - 单词
- `vim::Subword` - 子单词
- `vim::Sentence` - 句子
- `vim::Paragraph` - 段落
- `vim::Line` - 行
- `vim::CurrentLine` - 当前行
- `vim::EntireFile` - 整个文件
- `vim::Method` - 方法
- `vim::Class` - 类
- `vim::IndentObj` - 缩进对象
- `vim::Argument` - 参数
- `vim::Tag` - 标签
- `vim::Quotes` - 引号
- `vim::DoubleQuotes` - 双引号
- `vim::SingleQuotes` - 单引号
- `vim::BackQuotes` - 反引号
- `vim::MiniQuotes` - 小引号
- `vim::AnyQuotes` - 任意引号
- `vim::Parentheses` - 圆括号
- `vim::CurlyBrackets` - 花括号
- `vim::SquareBrackets` - 方括号
- `vim::AngleBrackets` - 尖括号
- `vim::VerticalBars` - 竖线
- `vim::MiniBrackets` - 小括号
- `vim::AnyBrackets` - 任意括号
- `vim::Matching` - 匹配
- `vim::UnmatchedForward` - 未匹配（向前）
- `vim::UnmatchedBackward` - 未匹配（向后）
- `vim::InnerObject` - 内部对象

### 大小写转换
- `vim::ChangeCase` - 改变大小写
- `vim::ConvertToLowerCase` - 转换为小写
- `vim::ConvertToUpperCase` - 转换为大写
- `vim::ConvertToOppositeCase` - 转换为相反大小写
- `vim::ConvertToRot13` - 转换为 ROT13
- `vim::ConvertToRot47` - 转换为 ROT47

### 数字操作
- `vim::Number` - 数字
- `vim::Increment` - 递增
- `vim::Decrement` - 递减

### 注释
- `vim::Comment` - 注释
- `vim::ToggleComments` - 切换注释

### 窗格操作
- `vim::ResizePaneUp` - 向上调整窗格大小
- `vim::ResizePaneDown` - 向下调整窗格大小
- `vim::ResizePaneLeft` - 向左调整窗格大小
- `vim::ResizePaneRight` - 向右调整窗格大小
- `vim::MaximizePane` - 最大化窗格
- `vim::ResetPaneSizes` - 重置窗格大小

### 其他
- `vim::Enter` - 回车
- `vim::Tab` - Tab
- `vim::Space` - 空格
- `vim::Backspace` - 退格
- `vim::Literal` - 字面量
- `vim::JoinLines` - 合并行
- `vim::JoinLinesNoWhitespace` - 合并行（无空白）
- `vim::Rewrap` - 重排
- `vim::Exchange` - 交换
- `vim::ClearExchange` - 清除交换
- `vim::ShowLocation` - 显示位置
- `vim::WrappingLeft` - 向左换行
- `vim::WrappingRight` - 向右换行
- `vim::RestoreVisualSelection` - 恢复可视选择
- `vim::VisualInsertFirstNonWhiteSpace` - 可视插入第一个非空白字符
- `vim::VisualInsertEndOfLine` - 可视插入行尾
- `vim::HelixAppend` - Helix 追加
- `vim::HelixInsert` - Helix 插入
- `vim::HelixSelectLine` - Helix 选择行
- `vim::HelixSelectRegex` - Helix 选择正则
- `vim::HelixSelectNext` - Helix 选择下一个
- `vim::HelixSelectPrevious` - Helix 选择上一个
- `vim::HelixGotoLastModification` - Helix 转到最后修改
- `vim::HelixKeepNewestSelection` - Helix 保持最新选择
- `vim::HelixCollapseSelection` - Helix 折叠选择
- `vim::HelixDuplicateAbove` - Helix 向上复制
- `vim::HelixDuplicateBelow` - Helix 向下复制
- `vim::ChangeListNewer` - 更改列表（较新）
- `vim::ChangeListOlder` - 更改列表（较旧）
- `vim::MoveToNext` - 移动到下一个
- `vim::MoveToPrevious` - 移动到上一个
- `vim::MoveToNextMatch` - 移动到下一个匹配
- `vim::MoveToPreviousMatch` - 移动到上一个匹配
- `vim::VisualCommand` - 可视命令
- `vim::ClearOperators` - 清除操作符

### Vim Push 操作（组合键）
- `vim::PushObject` - 推送对象
- `vim::PushFindForward` - 推送向前查找
- `vim::PushFindBackward` - 推送向后查找
- `vim::PushSneak` - 推送 Sneak
- `vim::PushSneakBackward` - 推送向后 Sneak
- `vim::PushChangeSurrounds` - 推送修改包围
- `vim::PushAddSurrounds` - 推送添加包围
- `vim::PushDeleteSurrounds` - 推送删除包围
- `vim::PushMark` - 推送标记
- `vim::PushJump` - 推送跳转
- `vim::PushRegister` - 推送寄存器
- `vim::PushRecordRegister` - 推送录制寄存器
- `vim::PushReplayRegister` - 推送重放寄存器
- `vim::PushReplace` - 推送替换
- `vim::PushDelete` - 推送删除
- `vim::PushChange` - 推送修改
- `vim::PushYank` - 推送复制
- `vim::PushIndent` - 推送缩进
- `vim::PushOutdent` - 推送取消缩进
- `vim::PushAutoIndent` - 推送自动缩进
- `vim::PushRewrap` - 推送重排
- `vim::PushShellCommand` - 推送 Shell 命令
- `vim::PushLowercase` - 推送小写
- `vim::PushUppercase` - 推送大写
- `vim::PushOppositeCase` - 推送相反大小写
- `vim::PushRot13` - 推送 ROT13
- `vim::PushRot47` - 推送 ROT47
- `vim::PushLiteral` - 推送字面量
- `vim::PushDigraph` - 推送二合字母
- `vim::PushReplaceWithRegister` - 推送用寄存器替换
- `vim::ToggleComments` - 推送切换注释
- `vim::PushForcedMotion` - 推送强制移动

### Helix Push 操作
- `vim::PushHelixNext` - 推送 Helix 下一个
- `vim::PushHelixPrevious` - 推送 Helix 上一个
- `vim::PushHelixMatch` - 推送 Helix 匹配
- `vim::PushHelixSurroundAdd` - 推送 Helix 添加包围
- `vim::PushHelixSurroundReplace` - 推送 Helix 替换包围
- `vim::PushHelixSurroundDelete` - 推送 Helix 删除包围

### Vim 视图
- `vim::ToggleMarksView` - 切换标记视图
- `vim::ToggleRegistersView` - 切换寄存器视图

### Vim 其他命令
- `vim::FindCommand` - 查找命令
- `vim::CountCommand` - 计数命令
- `vim::MenuSelectNext` - 菜单选择下一个
- `vim::MenuSelectPrevious` - 菜单选择上一个
- `vim::ShellCommand` - Shell 命令
- `vim::OpenDefaultKeymap` - 打开默认键映射
- `vim::ToggleProjectPanelFocus` - 切换项目面板焦点

## Terminal（终端）

- `terminal::Copy` - 复制
- `terminal::Paste` - 粘贴
- `terminal::Clear` - 清屏
- `terminal::RenameTerminal` - 重命名终端
- `terminal::SendText` - 发送文本
- `terminal::SendKeystroke` - 发送按键
- `terminal::RerunTask` - 重运行任务
- `terminal::ShowCharacterPalette` - 显示字符面板
- `terminal::ToggleViMode` - 切换 Vi 模式
- `terminal::SelectAll` - 全选
- `terminal::ScrollLineUp` - 向上滚动一行
- `terminal::ScrollLineDown` - 向下滚动一行
- `terminal::ScrollPageUp` - 向上滚动一页
- `terminal::ScrollPageDown` - 向下滚动一页
- `terminal::ScrollHalfPageUp` - 向上滚动半页
- `terminal::ScrollHalfPageDown` - 向下滚动半页
- `terminal::ScrollToTop` - 滚动到顶部
- `terminal::ScrollToBottom` - 滚动到底部
- `terminal::SearchTest` - 搜索测试
- `terminal_panel::Toggle` - 切换终端面板
- `terminal_panel::ToggleFocus` - 切换终端面板焦点

## Git

### 基本操作
- `git::Add` - 添加到暂存区
- `git::AddToGitignore` - 添加到 .gitignore
- `git::StageFile` - 暂存文件
- `git::UnstageFile` - 取消暂存文件
- `git::StageAll` - 暂存所有
- `git::UnstageAll` - 取消暂存所有
- `git::StageRange` - 暂存范围
- `git::ToggleStaged` - 切换暂存状态
- `git::StageAndNext` - 暂存并下一个
- `git::UnstageAndNext` - 取消暂存并下一个
- `git::Restore` - 还原
- `git::RestoreFile` - 还原文件
- `git::RestoreTrackedFiles` - 还原跟踪文件
- `git::TrashUntrackedFiles` - 删除未跟踪文件

### 提交
- `git::Commit` - 提交
- `git::Amend` - 修改提交
- `git::Signoff` - 签署
- `git::Uncommit` - 取消提交
- `git::GenerateCommitMessage` - 生成提交消息
- `git::ExpandCommitEditor` - 展开提交编辑器

### 分支
- `git::Branch` - 分支
- `git::Switch` - 切换分支
- `git::CheckoutBranch` - 检出分支
- `git::RenameBranch` - 重命名分支
- `branches::OpenRecent` - 打开最近的分支

### 远程操作
- `git::Fetch` - 获取
- `git::FetchFrom` - 从...获取
- `git::Pull` - 拉取
- `git::PullRebase` - 拉取并变基
- `git::Push` - 推送
- `git::ForcePush` - 强制推送
- `git::PushTo` - 推送到...
- `git::CreateRemote` - 创建远程

### Stash
- `git::StashAll` - 暂存所有
- `git::StashApply` - 应用暂存
- `git::StashPop` - 弹出暂存
- `git::ViewStash` - 查看暂存
- `git::ApplyCurrentStash` - 应用当前暂存
- `git::PopCurrentStash` - 弹出当前暂存
- `git::DropCurrentStash` - 丢弃当前暂存

### 工作树
- `git::Worktree` - 工作树
- `git::WorktreeFromDefault` - 从默认工作树
- `git::WorktreeFromDefaultOnWindow` - 在窗口中从默认工作树

### 查看差异和历史
- `git::Diff` - 差异
- `git::BranchDiff` - 分支差异
- `git::Blame` - Blame
- `git::FileHistory` - 文件历史
- `git::ViewCommitFromHistory` - 从历史查看提交
- `git::LoadMoreHistory` - 加载更多历史
- `git::OpenModifiedFiles` - 打开修改的文件

### 拉取请求
- `git::CreatePullRequest` - 创建拉取请求
- `git::LeaderAndFollower` - Leader 和 Follower

### 初始化和克隆
- `git::Init` - 初始化
- `git::Clone` - 克隆

### Git 面板
- `git_panel::Toggle` - 切换 Git 面板
- `git_panel::Close` - 关闭 Git 面板
- `git_panel::ToggleFocus` - 切换 Git 面板焦点
- `git_panel::FocusChanges` - 聚焦更改
- `git_panel::FocusEditor` - 聚焦编辑器
- `git_panel::OpenMenu` - 打开菜单
- `git_panel::ToggleTreeView` - 切换树视图
- `git_panel::ToggleSortByPath` - 切换按路径排序
- `git_panel::ToggleFillCoAuthors` - 切换填充共同作者
- `git_panel::NextEntry` - 下一个条目
- `git_panel::PreviousEntry` - 上一个条目
- `git_panel::FirstEntry` - 第一个条目
- `git_panel::LastEntry` - 最后一个条目
- `git_panel::ExpandSelectedEntry` - 展开选中的条目
- `git_panel::CollapseSelectedEntry` - 折叠选中的条目

### Git 选择器
- `git_picker::ActivateBranchesTab` - 激活分支标签
- `git_picker::ActivateStashTab` - 激活暂存标签
- `git_picker::ActivateWorktreesTab` - 激活工作树标签
- `branch_picker::FilterRemotes` - 过滤远程
- `branch_picker::DeleteBranch` - 删除分支
- `stash_picker::ShowStashItem` - 显示暂存项
- `stash_picker::DropStashItem` - 丢弃暂存项

### Git 图表
- `git_graph::Open` - 打开 Git 图表
- `git_graph::OpenCommitView` - 打开提交视图

## Project Panel（项目面板）

- `project_panel::Toggle` - 切换项目面板
- `project_panel::ToggleFocus` - 切换项目面板焦点
- `project_panel::Open` - 打开
- `project_panel::OpenPermanent` - 永久打开
- `project_panel::OpenSplitVertical` - 在垂直分割中打开
- `project_panel::OpenSplitHorizontal` - 在水平分割中打开
- `project_panel::OpenWithSystem` - 用系统默认程序打开
- `project_panel::NewFile` - 新建文件
- `project_panel::NewDirectory` - 新建目录
- `project_panel::Rename` - 重命名
- `project_panel::Delete` - 删除
- `project_panel::Trash` - 移到废纸篓
- `project_panel::Copy` - 复制
- `project_panel::Cut` - 剪切
- `project_panel::Paste` - 粘贴
- `project_panel::Duplicate` - 复制
- `project_panel::RemoveFromProject` - 从项目中移除
- `project_panel::RevealInFileManager` - 在文件管理器中显示
- `project_panel::CopyPath` - 复制路径
- `project_panel::CopyRelativePath` - 复制相对路径
- `project_panel::NewSearchInDirectory` - 在目录中新建搜索
- `project_panel::ExpandSelectedEntry` - 展开选中的条目
- `project_panel::CollapseSelectedEntry` - 折叠选中的条目
- `project_panel::CollapseAllEntries` - 折叠所有条目
- `project_panel::CollapseSelectedEntryAndChildren` - 折叠选中的条目及其子项
- `project_panel::FoldDirectory` - 折叠目录
- `project_panel::UnfoldDirectory` - 展开目录
- `project_panel::SelectParent` - 选择父级
- `project_panel::SelectNextDirectory` - 选择下一个目录
- `project_panel::SelectPrevDirectory` - 选择上一个目录
- `project_panel::SelectNextGitEntry` - 选择下一个 Git 条目
- `project_panel::SelectPrevGitEntry` - 选择上一个 Git 条目
- `project_panel::SelectNextDiagnostic` - 选择下一个诊断
- `project_panel::SelectPrevDiagnostic` - 选择上一个诊断
- `project_panel::CompareMarkedFiles` - 比较标记的文件
- `project_panel::ToggleHideHidden` - 切换隐藏隐藏文件
- `project_panel::ToggleHideGitIgnore` - 切换隐藏 .gitignore 文件
- `project_panel::DownloadFromRemote` - 从远程下载
- `project_panel::ScrollUp` - 向上滚动
- `project_panel::ScrollDown` - 向下滚动
- `project_panel::ScrollCursorTop` - 滚动光标到顶部
- `project_panel::ScrollCursorBottom` - 滚动光标到底部
- `project_panel::ScrollCursorCenter` - 滚动光标到中心

## Search（搜索）

### 缓冲区搜索
- `buffer_search::Deploy` - 部署缓冲区搜索
- `buffer_search::DeployReplace` - 部署替换
- `buffer_search::Dismiss` - 关闭缓冲区搜索
- `buffer_search::FocusEditor` - 聚焦编辑器

### 项目搜索
- `project_search::Toggle` - 切换项目搜索
- `project_search::ToggleFocus` - 切换项目搜索焦点
- `project_search::SearchInNew` - 在新窗口中搜索
- `project_search::ToggleFilters` - 切换过滤器
- `project_search::ToggleAllSearchResults` - 切换所有搜索结果
- `project_search::NextField` - 下一个字段

### 通用搜索
- `search::FocusSearch` - 聚焦搜索
- `search::ToggleReplace` - 切换替换
- `search::ToggleRegex` - 切换正则表达式
- `search::ToggleCaseSensitive` - 切换区分大小写
- `search::ToggleWholeWord` - 切换全词匹配
- `search::ToggleSelection` - 切换选择
- `search::ToggleIncludeIgnored` - 切换包含忽略的文件
- `search::SelectNextMatch` - 选择下一个匹配
- `search::SelectPreviousMatch` - 选择上一个匹配
- `search::SelectAllMatches` - 选择所有匹配
- `search::ReplaceNext` - 替换下一个
- `search::ReplaceAll` - 替换所有
- `search::NextHistoryQuery` - 下一个历史查询
- `search::PreviousHistoryQuery` - 上一个历史查询
- `search::CycleMode` - 循环模式

## File Finder（文件查找器）

- `file_finder::Toggle` - 切换文件查找器
- `file_finder::ToggleSplitMenu` - 切换分割菜单
- `file_finder::ToggleFilterMenu` - 切换过滤器菜单
- `file_finder::SelectPrevious` - 选择上一个
- `project_symbols::Toggle` - 切换项目符号

## Tab Switcher（标签切换器）

- `tab_switcher::Toggle` - 切换标签切换器
- `tab_switcher::ToggleAll` - 切换所有标签
- `tab_switcher::CloseSelectedItem` - 关闭选中的项
- `tab_switcher::OpenInActivePane` - 在活动窗格中打开

## Debugger（调试器）

### 会话控制
- `debugger::Start` - 启动调试
- `debugger::Stop` - 停止调试
- `debugger::Restart` - 重启调试
- `debugger::Rerun` - 重运行
- `debugger::RerunLastSession` - 重运行上次会话
- `debugger::RerunSession` - 重运行会话
- `debugger::Detach` - 分离
- `debugger::Pause` - 暂停
- `debugger::Continue` - 继续
- `debugger::StepOver` - 单步跳过
- `debugger::StepInto` - 单步进入
- `debugger::StepOut` - 单步跳出
- `debugger::StepBack` - 单步后退
- `debugger::RunToCursor` - 运行到光标

### 断点
- `debugger::ToggleBreakpoint` - 切换断点
- `debugger::ToggleEnableBreakpoint` - 切换启用断点
- `debugger::ToggleDataBreakpoint` - 切换数据断点
- `debugger::ToggleIgnoreBreakpoints` - 切换忽略断点
- `debugger::ClearAllBreakpoints` - 清除所有断点
- `debugger::UnsetBreakpoint` - 取消设置断点
- `debugger::EnableBreakpoint` - 启用断点
- `debugger::DisableBreakpoint` - 禁用断点
- `debugger::NextBreakpointProperty` - 下一个断点属性
- `debugger::PreviousBreakpointProperty` - 上一个断点属性

### 视图
- `debugger::ToggleSessionPicker` - 切换会话选择器
- `debugger::ToggleThreadPicker` - 切换线程选择器
- `debugger::ShowStackTrace` - 显示堆栈跟踪
- `debugger::FocusVariables` - 聚焦变量
- `debugger::FocusFrames` - 聚焦帧
- `debugger::FocusBreakpointList` - 聚焦断点列表
- `debugger::FocusModules` - 聚焦模块
- `debugger::FocusConsole` - 聚焦控制台
- `debugger::FocusTerminal` - 聚焦终端
- `debugger::FocusLoadedSources` - 聚焦已加载的源码
- `debugger::ToggleExpandItem` - 切换展开项
- `debugger::ToggleUserFrames` - 切换用户帧

### 调试面板
- `debug_panel::Toggle` - 切换调试面板
- `debug_panel::ToggleFocus` - 切换调试面板焦点

### 其他
- `debugger::EvaluateSelectedText` - 评估选中的文本
- `debugger::GoToSelectedAddress` - 转到选中的地址
- `debugger::OpenProjectDebugTasks` - 打开项目调试任务
- `debugger::ShutdownDebugAdapters` - 关闭调试适配器

### 变量列表
- `variable_list::AddWatch` - 添加监视
- `variable_list::RemoveWatch` - 移除监视
- `variable_list::EditVariable` - 编辑变量
- `variable_list::CopyVariableName` - 复制变量名
- `variable_list::CopyVariableValue` - 复制变量值
- `variable_list::GoToMemory` - 转到内存
- `variable_list::ExpandSelectedEntry` - 展开选中的条目
- `variable_list::CollapseSelectedEntry` - 折叠选中的条目

### 控制台
- `console::WatchExpression` - 监视表达式

### 新进程模态框
- `new_process_modal::ActivateLaunchTab` - 激活启动标签
- `new_process_modal::ActivateAttachTab` - 激活附加标签
- `new_process_modal::ActivateDebugTab` - 激活调试标签
- `new_process_modal::ActivateTaskTab` - 激活任务标签

## Assistant/Agent（助手/代理）

### 代理
- `agent::Chat` - 聊天
- `agent::Toggle` - 切换代理
- `agent::ToggleFocus` - 切换代理焦点
- `agent::NewThread` - 新建线程
- `agent::NewTextThread` - 新建文本线程
- `agent::NewExternalAgentThread` - 新建外部代理线程
- `agent::NewNativeAgentThreadFromSummary` - 从摘要新建原生代理线程
- `agent::ContinueThread` - 继续线程
- `agent::RemoveSelectedThread` - 移除选中的线程
- `agent::CopyThreadToClipboard` - 复制线程到剪贴板
- `agent::LoadThreadFromClipboard` - 从剪贴板加载线程
- `agent::OpenActiveThreadAsMarkdown` - 将活动线程作为 Markdown 打开
- `agent::OpenHistory` - 打开历史
- `agent::RemoveHistory` - 移除历史
- `agent::SendImmediately` - 立即发送
- `agent::SendNextQueuedMessage` - 发送下一个排队消息
- `agent::EditFirstQueuedMessage` - 编辑第一个排队消息
- `agent::RemoveFirstQueuedMessage` - 移除第一个排队消息
- `agent::ClearMessageQueue` - 清除消息队列
- `agent::ToggleModelSelector` - 切换模型选择器
- `agent::ToggleOptionsMenu` - 切换选项菜单
- `agent::ToggleNavigationMenu` - 切换导航菜单
- `agent::ToggleNewThreadMenu` - 切换新建线程菜单
- `agent::ToggleProfileSelector` - 切换配置选择器
- `agent::ToggleThinkingMode` - 切换思考模式
- `agent::ToggleThinkingEffortMenu` - 切换思考努力菜单
- `agent::CycleThinkingEffort` - 循环思考努力
- `agent::CycleFavoriteModels` - 循环收藏模型
- `agent::CycleModeSelector` - 循环模式选择器
- `agent::CycleNextInlineAssist` - 循环下一个内联助手
- `agent::CyclePreviousInlineAssist` - 循环上一个内联助手
- `agent::ExpandMessageEditor` - 展开消息编辑器
- `agent::InsertIntoEditor` - 插入到编辑器
- `agent::Split` - 分割
- `agent::Assist` - 助手
- `agent::ChatWithFollow` - 聊天并关注
- `agent::Follow` - 关注
- `agent::OpenSettings` - 打开设置
- `agent::OpenConfiguration` - 打开配置
- `agent::OpenAddContextMenu` - 打开添加上下文菜单
- `agent::OpenPermissionDropdown` - 打开权限下拉菜单
- `agent::ManageProfiles` - 管理配置
- `agent::SelectPermissionGranularity` - 选择权限粒度
- `agent::AuthorizeToolCall` - 授权工具调用
- `agent::AllowOnce` - 允许一次
- `agent::AllowAlways` - 总是允许
- `agent::RejectOnce` - 拒绝一次
- `agent::Reject` - 拒绝
- `agent::RejectAll` - 拒绝所有
- `agent::Keep` - 保留
- `agent::KeepAll` - 保留所有
- `agent::OpenAgentDiff` - 打开代理差异
- `agent::AddContextServer` - 添加上下文服务器
- `agent::AddSelectionToThread` - 添加选择到线程
- `agent::QuoteSelection` - 引用选择
- `agent::PasteRaw` - 粘贴原始内容
- `agent::ResetAgentZoom` - 重置代理缩放
- `agent::ResetTrialUpsell` - 重置试用升级
- `agent::ResetTrialEndUpsell` - 重置试用结束升级
- `agent::ReauthenticateAgent` - 重新认证代理
- `agent::FocusUp` - 向上聚焦
- `agent::FocusDown` - 向下聚焦
- `agent::FocusLeft` - 向左聚焦
- `agent::FocusRight` - 向右聚焦

### 助手
- `assistant::Assist` - 助手
- `assistant::Split` - 分割
- `assistant::InlineAssist` - 内联助手
- `assistant::QuoteSelection` - 引用选择
- `assistant::CopyCode` - 复制代码
- `assistant::InsertIntoEditor` - 插入到编辑器
- `assistant::ConfirmCommand` - 确认命令
- `assistant::ToggleModelSelector` - 切换模型选择器
- `assistant::ToggleFocus` - 切换焦点
- `assistant::ShowConfiguration` - 显示配置
- `assistant::DeployPromptLibrary` - 部署提示库
- `assistant::OpenRulesLibrary` - 打开规则库
- `assistant::CycleMessageRole` - 循环消息角色
- `assistant2::ToggleModelSelector` - 切换模型选择器（v2）

### 内联助手
- `inline_assistant::ThumbsUpResult` - 点赞结果
- `inline_assistant::ThumbsDownResult` - 点踩结果

### 规则库
- `rules_library::NewRule` - 新建规则
- `rules_library::DuplicateRule` - 复制规则
- `rules_library::DeleteRule` - 删除规则
- `rules_library::ToggleDefaultRule` - 切换默认规则
- `rules_library::RestoreDefaultContent` - 恢复默认内容

### 代理引导
- `agent::OpenOnboardingModal` - 打开引导模态框
- `agent::OpenClaudeAgentOnboardingModal` - 打开 Claude 代理引导模态框
- `agent::OpenAcpOnboardingModal` - 打开 ACP 代理引导模态框
- `agent::ResetOnboarding` - 重置引导

## Collab（协作）

### 基本协作
- `collab::ShareProject` - 共享项目
- `collab::CopyRoomId` - 复制房间 ID
- `collab::CopyLink` - 复制链接
- `collab::ScreenShare` - 屏幕共享
- `collab::Mute` - 静音
- `collab::Deafen` - 耳聋
- `collab::LeaveCall` - 离开通话
- `collab::OpenChannelNotes` - 打开频道笔记
- `collab::SwitchBranch` - 切换分支
- `collab::ToggleProjectMenu` - 切换项目菜单
- `collab::ToggleUserMenu` - 切换用户菜单
- `collab::SimulateUpdateAvailable` - 模拟更新可用

### 协作面板
- `collab_panel::Toggle` - 切换协作面板
- `collab_panel::ToggleFocus` - 切换协作面板焦点
- `collab_panel::Remove` - 移除
- `collab_panel::InsertSpace` - 插入空格
- `collab_panel::MoveSelected` - 移动选中的
- `collab_panel::MoveChannelUp` - 向上移动频道
- `collab_panel::MoveChannelDown` - 向下移动频道
- `collab_panel::StartMoveChannel` - 开始移动频道
- `collab_panel::ExpandSelectedChannel` - 展开选中的频道
- `collab_panel::CollapseSelectedChannel` - 折叠选中的频道
- `collab_panel::OpenSelectedChannelNotes` - 打开选中的频道笔记
- `collab_panel::Secondary` - 次要

### 频道模态框
- `channel_modal::ToggleMode` - 切换模式
- `channel_modal::ToggleMemberAdmin` - 切换成员管理员
- `channel_modal::RemoveMember` - 移除成员
- `channel_modal::SelectNextControl` - 选择下一个控件

### 客户端
- `client::SignIn` - 登录
- `client::SignOut` - 登出
- `client::Reconnect` - 重新连接

### 通知面板
- `notification_panel::Toggle` - 切换通知面板
- `notification_panel::ToggleFocus` - 切换通知面板焦点

### 活动指示器
- `activity_indicator::ShowErrorMessage` - 显示错误消息

## Menu（菜单）

- `menu::SelectFirst` - 选择第一个
- `menu::SelectLast` - 选择最后一个
- `menu::SelectNext` - 选择下一个
- `menu::SelectPrevious` - 选择上一个
- `menu::SelectParent` - 选择父级
- `menu::SelectChild` - 选择子级
- `menu::Confirm` - 确认
- `menu::SecondaryConfirm` - 次要确认
- `menu::Cancel` - 取消
- `menu::Restart` - 重新开始
- `menu::EndSlot` - 结束槽位

## App Menu（应用菜单）

- `app_menu::OpenApplicationMenu` - 打开应用菜单
- `app_menu::ActivateMenuLeft` - 激活左侧菜单
- `app_menu::ActivateMenuRight` - 激活右侧菜单

## Panel（面板）

- `panel::PreviousPanelTab` - 上一个面板标签
- `panel::NextPanelTab` - 下一个面板标签

## Outline（大纲）

- `outline::Toggle` - 切换大纲
- `outline_panel::Toggle` - 切换大纲面板
- `outline_panel::ToggleFocus` - 切换大纲面板焦点
- `outline_panel::ToggleActiveEditorPin` - 切换活动编辑器固定
- `outline_panel::OpenSelectedEntry` - 打开选中的条目
- `outline_panel::ExpandSelectedEntry` - 展开选中的条目
- `outline_panel::ExpandAllEntries` - 展开所有条目
- `outline_panel::CollapseSelectedEntry` - 折叠选中的条目
- `outline_panel::CollapseAllEntries` - 折叠所有条目
- `outline_panel::FoldDirectory` - 折叠目录
- `outline_panel::UnfoldDirectory` - 展开目录
- `outline_panel::SelectParent` - 选择父级
- `outline_panel::RevealInFileManager` - 在文件管理器中显示
- `outline_panel::CopyPath` - 复制路径
- `outline_panel::CopyRelativePath` - 复制相对路径
- `outline_panel::ScrollUp` - 向上滚动
- `outline_panel::ScrollDown` - 向下滚动
- `outline_panel::ScrollCursorTop` - 滚动光标到顶部
- `outline_panel::ScrollCursorBottom` - 滚动光标到底部
- `outline_panel::ScrollCursorCenter` - 滚动光标到中心

## Settings（设置）

### 设置编辑器
- `settings_editor::Minimize` - 最小化
- `settings_editor::FocusFile` - 聚焦文件
- `settings_editor::FocusNextFile` - 聚焦下一个文件
- `settings_editor::FocusPreviousFile` - 聚焦上一个文件
- `settings_editor::OpenCurrentFile` - 打开当前文件
- `settings_editor::ToggleFocusNav` - 切换聚焦导航
- `settings_editor::FocusNavEntry` - 聚焦导航条目
- `settings_editor::FocusFirstNavEntry` - 聚焦第一个导航条目
- `settings_editor::FocusLastNavEntry` - 聚焦最后一个导航条目
- `settings_editor::FocusNextNavEntry` - 聚焦下一个导航条目
- `settings_editor::FocusPreviousNavEntry` - 聚焦上一个导航条目
- `settings_editor::FocusNextRootNavEntry` - 聚焦下一个根导航条目
- `settings_editor::FocusPreviousRootNavEntry` - 聚焦上一个根导航条目
- `settings_editor::ExpandNavEntry` - 展开导航条目
- `settings_editor::CollapseNavEntry` - 折叠导航条目

### 设置配置选择器
- `settings_profile_selector::Toggle` - 切换设置配置选择器

## Theme（主题）

- `theme_selector::Toggle` - 切换主题选择器
- `theme_selector::Reload` - 重新加载主题
- `icon_theme_selector::Toggle` - 切换图标主题选择器

## Language（语言）

- `language_selector::Toggle` - 切换语言选择器
- `encoding_selector::Toggle` - 切换编码选择器
- `line_ending_selector::Toggle` - 切换行结束符选择器

## Snippets（代码片段）

- `snippets::ConfigureSnippets` - 配置代码片段
- `snippets::OpenFolder` - 打开文件夹

## Toolchain（工具链）

- `toolchain::AddToolchain` - 添加工具链
- `toolchain::Select` - 选择工具链

## Notebook/REPL（笔记本/REPL）

### 笔记本
- `notebook::OpenNotebook` - 打开笔记本
- `notebook::Run` - 运行
- `notebook::RunAll` - 运行所有
- `notebook::AddCodeBlock` - 添加代码块
- `notebook::AddMarkdownBlock` - 添加 Markdown 块
- `notebook::MoveCellUp` - 向上移动单元格
- `notebook::MoveCellDown` - 向下移动单元格
- `notebook::ClearOutputs` - 清除输出
- `notebook::RestartKernel` - 重启内核
- `notebook::InterruptKernel` - 中断内核

### REPL
- `repl::Run` - 运行
- `repl::RunInPlace` - 原地运行
- `repl::Sessions` - 会话
- `repl::Restart` - 重启
- `repl::Interrupt` - 中断
- `repl::Shutdown` - 关闭
- `repl::ClearOutputs` - 清除输出
- `repl::RefreshKernelspecs` - 刷新内核规格

## Copilot

- `copilot::SignIn` - 登录
- `copilot::SignOut` - 登出
- `copilot::Reinstall` - 重新安装
- `copilot::Suggest` - 建议
- `copilot::NextSuggestion` - 下一个建议
- `copilot::PreviousSuggestion` - 上一个建议

## Supermaven

- `supermaven::SignOut` - 登出

## Diagnostics（诊断）

- `diagnostics::Deploy` - 部署诊断
- `diagnostics::DeployCurrentFile` - 部署当前文件诊断
- `diagnostics::ToggleWarnings` - 切换警告
- `diagnostics::ToggleDiagnosticsRefresh` - 切换诊断刷新

## Task（任务）

- `task::Spawn` - 生成任务
- `task::Rerun` - 重运行任务

## Zed 核心

### 文件和设置
- `zed::OpenSettings` - 打开设置
- `zed::OpenSettingsFile` - 打开设置文件
- `zed::OpenSettingsAt` - 在指定位置打开设置
- `zed::OpenDefaultSettings` - 打开默认设置
- `zed::OpenKeymap` - 打开键映射
- `zed::OpenKeymapFile` - 打开键映射文件
- `zed::OpenDefaultKeymap` - 打开默认键映射
- `zed::OpenProjectSettings` - 打开项目设置
- `zed::OpenProjectSettingsFile` - 打开项目设置文件
- `zed::OpenAccountSettings` - 打开账户设置
- `zed::OpenBrowser` - 打开浏览器
- `zed::OpenDocs` - 打开文档
- `zed::OpenLicenses` - 打开许可证
- `zed::OpenLog` - 打开日志
- `zed::OpenOnboarding` - 打开引导
- `zed::OpenPerformanceProfiler` - 打开性能分析器
- `zed::OpenTelemetryLog` - 打开遥测日志
- `zed::OpenServerSettings` - 打开服务器设置
- `zed::OpenDebugTasks` - 打开调试任务
- `zed::OpenTasks` - 打开任务
- `zed::OpenProjectTasks` - 打开项目任务
- `zed::OpenZedUrl` - 打开 Zed URL
- `zed::OpenZedRepo` - 打开 Zed 仓库

### 字体大小
- `zed::IncreaseBufferFontSize` - 增大缓冲区字体大小
- `zed::DecreaseBufferFontSize` - 减小缓冲区字体大小
- `zed::ResetBufferFontSize` - 重置缓冲区字体大小
- `zed::IncreaseUiFontSize` - 增大 UI 字体大小
- `zed::DecreaseUiFontSize` - 减小 UI 字体大小
- `zed::ResetUiFontSize` - 重置 UI 字体大小

### 窗口和视图
- `zed::Minimize` - 最小化
- `zed::Hide` - 隐藏
- `zed::HideOthers` - 隐藏其他
- `zed::ShowAll` - 显示所有
- `zed::Zoom` - 缩放
- `zed::ToggleFullScreen` - 切换全屏
- `zed::ResetAllZoom` - 重置所有缩放

### 应用程序
- `zed::About` - 关于
- `zed::Quit` - 退出
- `zed::Extensions` - 扩展
- `zed::ReloadExtensions` - 重新加载扩展
- `zed::InstallDevExtension` - 安装开发扩展

### 项目
- `projects::OpenRecent` - 打开最近的项目
- `projects::OpenRemote` - 打开远程项目
- `projects::OpenDevContainer` - 打开 Dev Container
- `projects::InitializeDevContainer` - 初始化 Dev Container

### 其他
- `zed::RevealLogInFileManager` - 在文件管理器中显示日志
- `zed::DebugElements` - 调试元素
- `zed::TestCrash` - 测试崩溃
- `zed::TestPanic` - 测试恐慌
- `zed::ResetDatabase` - 重置数据库
- `zed::ShowWelcome` - 显示欢迎
- `zed::ImportVsCodeSettings` - 导入 VS Code 设置
- `zed::ImportCursorSettings` - 导入 Cursor 设置
- `zed::ToggleBaseKeymapSelector` - 切换基础键映射选择器
- `zed::ShowDefaultSemanticTokenRules` - 显示默认语义令牌规则
- `zed::CopySystemSpecsIntoClipboard` - 复制系统规格到剪贴板
- `zed::NoAction` - 无操作

### Zed Actions
- `zed_actions::OpenSettings` - 打开设置
- `zed_actions::OpenSettingsEditor` - 打开设置编辑器
- `zed_actions::OpenKeymap` - 打开键映射
- `zed_actions::OpenKeymapEditor` - 打开键映射编辑器
- `zed_actions::OpenProjectSettings` - 打开项目设置

### 多工作区
- `multi_workspace::ToggleWorkspaceSidebar` - 切换工作区侧边栏
- `multi_workspace::FocusWorkspaceSidebar` - 聚焦工作区侧边栏
- `multi_workspace::NewWorkspaceInWindow` - 在窗口中新建工作区
- `multi_workspace::PreviousWorkspaceInWindow` - 窗口中的上一个工作区
- `multi_workspace::NextWorkspaceInWindow` - 窗口中的下一个工作区

## Window（窗口）

- `window::MergeAllWindows` - 合并所有窗口
- `window::MoveTabToNewWindow` - 将标签移到新窗口
- `window::ShowNextWindowTab` - 显示下一个窗口标签
- `window::ShowPreviousWindowTab` - 显示上一个窗口标签

## Command Palette（命令面板）

- `command_palette::Toggle` - 切换命令面板

## Picker（选择器）

- `picker::ConfirmCompletion` - 确认补全
- `picker::ConfirmInput` - 确认输入

## Go To Line（转到行）

- `go_to_line::Toggle` - 切换转到行

## Journal（日志）

- `journal::NewJournalEntry` - 新建日志条目

## CLI

- `cli::InstallCliBinary` - 安装 CLI 二进制文件
- `cli::RegisterZedScheme` - 注册 Zed 方案

## Image Viewer（图像查看器）

- `image_viewer::ZoomIn` - 放大
- `image_viewer::ZoomOut` - 缩小
- `image_viewer::ResetZoom` - 重置缩放
- `image_viewer::ZoomToActualSize` - 缩放到实际大小
- `image_viewer::FitToView` - 适应视图

## Markdown（Markdown）

- `markdown::OpenPreview` - 打开预览
- `markdown::OpenPreviewToTheSide` - 在侧边打开预览
- `markdown::OpenFollowingPreview` - 打开跟随预览
- `markdown::Copy` - 复制
- `markdown::CopyAsMarkdown` - 复制为 Markdown
- `markdown::ScrollUp` - 向上滚动
- `markdown::ScrollDown` - 向下滚动
- `markdown::ScrollPageUp` - 向上翻页
- `markdown::ScrollPageDown` - 向下翻页
- `markdown::MovePageUp` - 向上移动一页
- `markdown::MovePageDown` - 向下移动一页
- `markdown::ScrollUpByItem` - 按项向上滚动
- `markdown::ScrollDownByItem` - 按项向下滚动

## SVG

- `svg::OpenPreview` - 打开预览
- `svg::OpenPreviewToTheSide` - 在侧边打开预览
- `svg::OpenFollowingPreview` - 打开跟随预览

## Toast

- `toast::RunAction` - 运行操作

## Action

- `action::Sequence` - 序列操作

## Context Server（上下文服务器）

- `context_server::Restart` - 重启上下文服务器

## Highlights Tree View（高亮树视图）

- `highlights_tree_view::ToggleTextHighlights` - 切换文本高亮
- `highlights_tree_view::ToggleSemanticTokens` - 切换语义令牌

## Syntax Tree View（语法树视图）

- `syntax_tree_view::UseActiveEditor` - 使用活动编辑器

## LSP Tool（LSP 工具）

- `lsp_tool::ToggleMenu` - 切换菜单

## Keymap Editor（键映射编辑器）

- `keymap_editor::CreateBinding` - 创建绑定
- `keymap_editor::EditBinding` - 编辑绑定
- `keymap_editor::DeleteBinding` - 删除绑定
- `keymap_editor::OpenCreateKeybindingModal` - 打开创建键映射模态框
- `keymap_editor::CopyAction` - 复制操作
- `keymap_editor::CopyContext` - 复制上下文
- `keymap_editor::ShowMatchingKeybinds` - 显示匹配的键绑定
- `keymap_editor::ToggleConflictFilter` - 切换冲突过滤器
- `keymap_editor::ToggleKeystrokeSearch` - 切换按键搜索
- `keymap_editor::ToggleExactKeystrokeMatching` - 切换精确按键匹配

## Keystroke Input（按键输入）

- `keystroke_input::StartRecording` - 开始录制
- `keystroke_input::StopRecording` - 停止录制
- `keystroke_input::ClearKeystrokes` - 清除按键

## Feedback（反馈）

- `feedback::EmailZed` - 给 Zed 发邮件
- `feedback::FileBugReport` - 提交错误报告
- `feedback::RequestFeature` - 请求功能

## Auto Update（自动更新）

- `auto_update::Check` - 检查更新
- `auto_update::DismissMessage` - 关闭消息
- `auto_update::ViewReleaseNotes` - 查看发行说明
- `auto_update::ViewReleaseNotesLocally` - 在本地查看发行说明

## Onboarding（引导）

- `onboarding::SignIn` - 登录
- `onboarding::OpenAccount` - 打开账户
- `onboarding::ResetHints` - 重置提示
- `onboarding::Finish` - 完成

## Git Onboarding（Git 引导）

- `git_onboarding::OpenGitIntegrationOnboarding` - 打开 Git 集成引导

## Zed Predict Onboarding（Zed Predict 引导）

- `zed_predict_onboarding::OpenZedPredictOnboarding` - 打开 Zed Predict 引导

## Recent Projects（最近项目）

- `recent_projects::ToggleActionsMenu` - 切换操作菜单

## Welcome（欢迎）

- `welcome::OpenRecentProject` - 打开最近的项目

## Dev（开发）

### 调试工具
- `dev::ToggleInspector` - 切换检查器
- `dev::CaptureRecentAudio` - 捕获最近的音频
- `dev::OpenUrlPrompt` - 打开 URL 提示
- `dev::OpenThemePreview` - 打开主题预览
- `dev::OpenSyntaxTreeView` - 打开语法树视图
- `dev::OpenHighlightsTreeView` - 打开高亮树视图
- `dev::OpenKeyContextView` - 打开键上下文视图
- `dev::OpenLanguageServerLogs` - 打开语言服务器日志
- `dev::OpenDebugAdapterLogs` - 打开调试适配器日志
- `dev::OpenAcpLogs` - 打开 ACP 日志
- `dev::OpenEditPredictionContextView` - 打开编辑预测上下文视图
- `dev::CopyDebugAdapterArguments` - 复制调试适配器参数
- `dev::EditPredictionContextGoBack` - 编辑预测上下文后退
- `dev::EditPredictionContextGoForward` - 编辑预测上下文前进

### 远程调试
- `remote_debug::SimulateTimeout` - 模拟超时
- `remote_debug::SimulateTimeoutExhausted` - 模拟超时耗尽
- `remote_debug::SimulateDisconnect` - 模拟断开连接

## Edit Prediction（编辑预测）

- `edit_prediction::ToggleMenu` - 切换菜单
- `edit_prediction::RatePredictions` - 评价预测
- `edit_prediction::CaptureExample` - 捕获示例
- `edit_prediction::ClearHistory` - 清除历史
- `edit_prediction::ResetOnboarding` - 重置引导

## Zeta

- `zeta::NextEdit` - 下一个编辑
- `zeta::PreviousEdit` - 上一个编辑
- `zeta::PreviewPrediction` - 预览预测
- `zeta::FocusPredictions` - 聚焦预测
- `zeta::ThumbsUpActivePrediction` - 点赞活动预测
- `zeta::ThumbsDownActivePrediction` - 点踩活动预测

## Bedrock

- `bedrock::Tab` - Tab
- `bedrock::TabPrev` - 反向 Tab

## 其他

- `""` - 空操作（无操作）

